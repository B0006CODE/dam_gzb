<template>
  <div class="dimension-filter-container">
    <svg 
      class="filter-svg" 
      viewBox="0 0 300 300" 
      width="300" 
      height="300"
    >
      <defs>
        <!-- 核心区白色渐变 -->
        <radialGradient id="core-gradient" cx="0" cy="1" r="1">
          <stop offset="0%" stop-color="#ffffff" />
          <stop offset="80%" stop-color="#f0f9ff" />
          <stop offset="100%" stop-color="#e0f2fe" />
        </radialGradient>
        
        <!-- 核心区阴影 -->
        <filter id="core-shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="rgba(56, 189, 248, 0.5)" />
        </filter>

        <!-- 扇形区阴影 -->
        <filter id="sector-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.3)" />
        </filter>
      </defs>

      <!-- 菜单层 (位于底层) -->
      <g class="menu-layer" :class="{ expanded: isExpanded }">
        <g 
          v-for="(dim, index) in dimensions" 
          :key="dim.key"
          class="sector-group"
          :class="{ 
            active: !hiddenDimensions.includes(dim.key),
            inactive: hiddenDimensions.includes(dim.key)
          }"
          @click="toggleDimension(dim.key)"
          @mouseenter="hoveredSector = index"
          @mouseleave="hoveredSector = null"
        >
          <!-- 扇形块 -->
          <path
            :d="getSectorPath(index)"
            :fill="getSectorColor(dim, index)"
            class="sector-path"
          />
          
          <!-- 径向文字 -->
          <text
            :x="getTextPosition(index).x"
            :y="getTextPosition(index).y"
            :transform="getTextRotation(index)"
            class="sector-text"
            text-anchor="middle"
            dominant-baseline="middle"
          >
            {{ dim.label }}
          </text>
        </g>
      </g>

      <!-- 核心层 (位于顶层) -->
      <g 
        class="core-layer" 
        @click="toggleExpand"
        @mouseenter="isCoreHovered = true"
        @mouseleave="isCoreHovered = false"
      >
        <!-- 核心圆盘背景 -->
        <path 
          d="M 0 300 L 0 210 A 90 90 0 0 1 90 300 Z" 
          fill="url(#core-gradient)"
          filter="url(#core-shadow)"
          class="core-bg"
        />
        
        <!-- 刻度线装饰 -->
        <g class="ticks">
          <line 
            v-for="i in 20" 
            :key="i"
            :x1="getTickCoords(i).x1" 
            :y1="getTickCoords(i).y1"
            :x2="getTickCoords(i).x2" 
            :y2="getTickCoords(i).y2"
            stroke="#bae6fd"
            stroke-width="1.5"
          />
        </g>

        <!-- 漏斗图标 -->
        <g transform="translate(25, 275) scale(1.2)" class="core-icon">
          <path 
            d="M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z" 
            fill="#0ea5e9"
          />
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { getDimensionList } from '@/utils/nodeColorMapper';

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['update:modelValue']);

const isExpanded = ref(false);
const hoveredSector = ref(null);
const isCoreHovered = ref(false);

// 几何参数
const R_CORE = 90;
const R_INNER = 90;
const R_OUTER = 240;
const R_TEXT = 165; // 文字半径位置

// 获取维度列表
const dimensions = computed(() => getDimensionList());

// 当前隐藏的维度
const hiddenDimensions = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

const toggleDimension = (dimKey) => {
  const current = [...hiddenDimensions.value];
  const index = current.indexOf(dimKey);
  
  if (index === -1) {
    current.push(dimKey);
  } else {
    current.splice(index, 1);
  }
  
  hiddenDimensions.value = [...current];
};

// 辅助函数：角度转弧度
const toRad = (deg) => deg * Math.PI / 180;

// 计算扇形路径
// 坐标系：原点(0,0)在左上角。圆心在(0,300)。
// 角度：从Y轴负向(向上)为0度？不，我们直接用三角函数计算。
// 0度对应(0, 210)点（正上方），90度对应(90, 300)点（正右方）。
// 实际上是从 0度(垂直向上) 到 90度(水平向右) 扫过。
const getSectorPath = (index) => {
  const total = dimensions.value.length;
  const anglePerSector = 90 / total;
  
  // 顺时针排列：从 0 度开始
  const startAngle = index * anglePerSector;
  const endAngle = (index + 1) * anglePerSector;
  
  // 转换为弧度 (注意 SVG 坐标系 Y 轴向下)
  // 0度时，向量为 (0, -1)。90度时，向量为 (1, 0)。
  // 使用 sin/cos 变换：
  // x = r * sin(angle)
  // y = 300 - r * cos(angle)
  
  const x1_in = R_INNER * Math.sin(toRad(startAngle));
  const y1_in = 300 - R_INNER * Math.cos(toRad(startAngle));
  
  const x2_out = R_OUTER * Math.sin(toRad(startAngle));
  const y2_out = 300 - R_OUTER * Math.cos(toRad(startAngle));
  
  const x3_out = R_OUTER * Math.sin(toRad(endAngle));
  const y3_out = 300 - R_OUTER * Math.cos(toRad(endAngle));
  
  const x4_in = R_INNER * Math.sin(toRad(endAngle));
  const y4_in = 300 - R_INNER * Math.cos(toRad(endAngle));
  
  return `
    M ${x1_in} ${y1_in}
    L ${x2_out} ${y2_out}
    A ${R_OUTER} ${R_OUTER} 0 0 1 ${x3_out} ${y3_out}
    L ${x4_in} ${y4_in}
    A ${R_INNER} ${R_INNER} 0 0 0 ${x1_in} ${y1_in}
    Z
  `;
};

// 计算文字位置
const getTextPosition = (index) => {
  const total = dimensions.value.length;
  const anglePerSector = 90 / total;
  const midAngle = (index + 0.5) * anglePerSector;
  
  return {
    x: R_TEXT * Math.sin(toRad(midAngle)),
    y: 300 - R_TEXT * Math.cos(toRad(midAngle))
  };
};

// 计算文字旋转
const getTextRotation = (index) => {
  const total = dimensions.value.length;
  const anglePerSector = 90 / total;
  const midAngle = (index + 0.5) * anglePerSector;
  
  // 文字需要顺时针旋转 midAngle - 90 度 (如果字头朝内)
  // 或者 midAngle 度 (如果字头朝外？)
  // 让我们试一下：
  // 0度时(垂直向上)，文字应该水平？不，参考图文字沿半径。
  // 0度时，半径竖直向上，文字应该竖直，字头朝左？参考图字头朝外。
  // 0度时，文字应该旋转 -90度？
  // 让我们看参考图：最左边的文字几乎是水平的，最下边的文字几乎是垂直的。
  // 实际上参考图是从左到右排列。
  // 我们的 0度是垂直向上。
  // 那么 midAngle 对应的旋转应该是 midAngle - 90。
  
  const pos = getTextPosition(index);
  return `rotate(${midAngle - 90}, ${pos.x}, ${pos.y})`;
};

// 计算刻度线坐标
const getTickCoords = (i) => {
  const totalTicks = 20;
  const angleStep = 90 / totalTicks;
  const angle = i * angleStep;
  
  const r_start = 65;
  const r_end = 75;
  
  return {
    x1: r_start * Math.sin(toRad(angle)),
    y1: 300 - r_start * Math.cos(toRad(angle)),
    x2: r_end * Math.sin(toRad(angle)),
    y2: 300 - r_end * Math.cos(toRad(angle))
  };
};

const getSectorColor = (dim, index) => {
  const isActive = !hiddenDimensions.value.includes(dim.key);
  const isHovered = hoveredSector.value === index;
  
  if (!isActive) return '#cbd5e1'; // 灰色
  
  // 增加亮度以匹配参考图的鲜艳感
  return isHovered ? dim.light : dim.main;
};

</script>

<style lang="less" scoped>
.dimension-filter-container {
  position: absolute;
  left: 0;
  bottom: 0;
  z-index: 1000;
  pointer-events: none;
}

.filter-svg {
  pointer-events: none;
  overflow: visible;
}

.core-layer {
  cursor: pointer;
  pointer-events: auto;
  transition: transform 0.3s ease;
  
  &:hover {
    transform: scale(1.02);
    transform-origin: 0 300px;
  }
  
  .core-bg {
    transition: fill 0.3s ease;
  }
}

.menu-layer {
  opacity: 0;
  transform: scale(0.5);
  transform-origin: 0 300px;
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  pointer-events: none;
  
  &.expanded {
    opacity: 1;
    transform: scale(1);
    pointer-events: auto;
  }
}

.sector-group {
  cursor: pointer;
  transition: opacity 0.3s ease;
  
  &.inactive {
    opacity: 0.6;
    filter: grayscale(100%);
  }
  
  &:hover {
    opacity: 1;
    filter: brightness(1.1);
  }
}

.sector-path {
  stroke: #fff;
  stroke-width: 2px;
  transition: fill 0.3s ease;
}

.sector-text {
  fill: #fff;
  font-size: 14px;
  font-weight: bold;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
</style>
