<template>
  <div class="exception-qa-view">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="hero-kicker">异常问答服务</span>
        <h2>异常接口问答</h2>
        <p>
          展示异常问答服务的调用记录、最新结果和异常统计信息，便于跟踪外部系统的接入与使用情况。
        </p>
      </div>

      <div class="hero-actions">
        <div class="signal-card">
          <span class="signal-label">最近调用时间</span>
          <strong>{{ latestRecord ? formatRecordTime(latestRecord.asked_at) : '-' }}</strong>
          <span class="signal-sub">{{ latestRecord ? formatRelativeTime(latestRecord.asked_at) : '暂无记录' }}</span>
        </div>
        <div class="hero-mini-metrics">
          <div class="hero-mini-card">
            <span>调用记录数</span>
            <strong>{{ records.length }}</strong>
          </div>
          <div class="hero-mini-card">
            <span>最新异常数</span>
            <strong>{{ latestStats.total_count || 0 }}</strong>
          </div>
        </div>
        <button
          class="refresh-btn"
          type="button"
          :disabled="loading"
          @click="loadRecords()"
        >
          {{ loading ? '刷新中' : '刷新' }}
        </button>
      </div>
    </section>

    <section class="overview-grid">
      <article
        v-for="item in overviewCards"
        :key="item.label"
        class="overview-card"
      >
        <span class="overview-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <span class="overview-note">{{ item.note }}</span>
      </article>
    </section>

    <section class="dashboard-shell">
      <aside class="intel-panel">
        <div class="panel-head">
          <span>最新记录</span>
          <strong>{{ latestRecord ? '已更新' : '暂无数据' }}</strong>
        </div>

        <div v-if="latestRecord" class="latest-brief">
          <div class="brief-block">
            <span class="brief-label">最新问题</span>
            <p>{{ latestRecord.question }}</p>
          </div>

          <div class="brief-grid">
            <div class="brief-metric">
              <span>来源系统</span>
              <strong>{{ latestRecord.source_system || 'unknown' }}</strong>
            </div>
            <div class="brief-metric">
              <span>异常测点</span>
              <strong>{{ latestStats.total_count || 0 }}</strong>
            </div>
          </div>

          <div class="brief-block">
            <span class="brief-label">主要异常类型</span>
            <div class="chip-list">
              <span
                v-for="item in topInstrumentChips"
                :key="item.label"
                class="info-chip"
              >
                {{ item.label }}
              </span>
            </div>
          </div>

          <div class="brief-block">
            <span class="brief-label">主要异常区域</span>
            <div class="chip-list">
              <span
                v-for="item in topAreaChips"
                :key="item.label"
                class="info-chip area"
              >
                {{ item.label }}
              </span>
            </div>
          </div>
        </div>

        <div v-else class="panel-empty">
          暂无异常问答调用记录。
        </div>
      </aside>

      <main class="records-panel">
        <div class="records-head">
          <div>
            <span class="section-kicker">调用记录</span>
            <h3>异常问答记录</h3>
          </div>
          <span class="record-count">{{ records.length }} 条</span>
        </div>

        <div v-if="loading && !records.length" class="state-tip">
          正在整理异常问答记录...
        </div>
        <div v-else-if="!records.length" class="state-tip empty">
          当前暂无调用记录。
        </div>
        <div v-else class="record-list scrollbar-custom">
          <article
            v-for="(item, index) in records"
            :key="item.record_id || `${item.asked_at}-${item.question}`"
            class="record-item"
            :style="{ animationDelay: `${index * 70}ms` }"
          >
            <div class="record-rail">
              <span class="rail-dot"></span>
              <span class="rail-line"></span>
            </div>

            <div class="record-card">
              <header class="record-meta">
                <div class="meta-main">
                  <span class="record-time">{{ formatRecordTime(item.asked_at) }}</span>
                  <span class="record-relative">{{ formatRelativeTime(item.asked_at) }}</span>
                </div>
                <div class="meta-tags">
                  <span class="source-tag">{{ item.source_system || 'unknown' }}</span>
                  <span class="mode-tag">{{ getResponseTypeLabel(item.response_type) }}</span>
                  <span v-if="item.is_fallback" class="fallback-tag">兜底建议</span>
                </div>
              </header>

              <section class="question-block">
                <span class="block-label">问题</span>
                <p>{{ item.question }}</p>
              </section>

              <section
                v-if="item.problems?.length || item.suggestions?.length"
                class="analysis-grid"
              >
                <article v-if="item.problems?.length" class="analysis-panel problem-panel">
                  <div class="panel-title-row">
                    <span class="block-label">出现问题</span>
                    <span class="panel-counter">{{ item.problems.length }} 条</span>
                  </div>
                  <ul class="insight-list">
                    <li v-for="problem in item.problems" :key="problem">
                      {{ problem }}
                    </li>
                  </ul>
                </article>

                <article v-if="item.suggestions?.length" class="analysis-panel suggestion-panel">
                  <div class="panel-title-row">
                    <span class="block-label">建议解决方案</span>
                    <span class="panel-counter">{{ item.suggestions.length }} 条</span>
                  </div>
                  <ol class="insight-list ordered">
                    <li v-for="suggestion in item.suggestions" :key="suggestion">
                      {{ suggestion }}
                    </li>
                  </ol>
                </article>
              </section>

              <section v-if="item.stats_summary" class="stats-summary-block">
                <div class="answer-head">
                  <span class="block-label">统计摘要</span>
                  <div class="answer-stats">
                    <span v-if="item.retrieval?.skipped" class="mini-chip subtle-chip">
                      纯统计模式
                    </span>
                    <span v-else-if="item.retrieval?.used" class="mini-chip subtle-chip">
                      含检索上下文
                    </span>
                  </div>
                </div>
                <div
                  class="answer-rich-text summary-rich-text"
                  v-html="renderAnswer(item.stats_summary)"
                ></div>
              </section>

              <section v-if="item.answer" class="answer-block">
                <div class="answer-head">
                  <span class="block-label">回答</span>
                  <div class="answer-stats">
                    <span v-if="item.exception_points_total" class="mini-chip">
                      {{ item.exception_points_total }} 个测点
                    </span>
                    <span v-if="item.stats?.total_count" class="mini-chip">
                      {{ item.stats.total_count }} 个异常
                    </span>
                    <span v-if="item.retrieval?.retrieval_mode" class="mini-chip subtle-chip">
                      {{ getRetrievalModeLabel(item.retrieval?.retrieval_mode) }}
                    </span>
                  </div>
                </div>
                <div
                  class="answer-rich-text"
                  v-html="renderAnswer(item.answer || '暂无回答内容')"
                ></div>
              </section>

              <footer v-if="buildRecordFootnotes(item).length" class="record-foot">
                <span
                  v-for="foot in buildRecordFootnotes(item)"
                  :key="foot"
                  class="foot-chip"
                >
                  {{ foot }}
                </span>
              </footer>
            </div>
          </article>
        </div>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { message } from 'ant-design-vue';
import { marked } from 'marked';

import { damExceptionQaApi } from '@/apis/system_api';
import { formatRelative, parseToShanghai } from '@/utils/time';

marked.setOptions({
  gfm: true,
  breaks: true,
  mangle: false,
  headerIds: false,
});

const loading = ref(false);
const records = ref([]);

const formatRecordTime = (isoTime) => {
  if (!isoTime) return '-';
  const date = parseToShanghai(isoTime);
  if (date) return date.format('YYYY/MM/DD HH:mm:ss');
  const fallback = new Date(isoTime);
  if (Number.isNaN(fallback.getTime())) return isoTime;
  return fallback.toLocaleString('zh-CN', { hour12: false });
};

const formatRelativeTime = (isoTime) => {
  if (!isoTime) return '未知时间';
  return formatRelative(isoTime);
};

const sortEntries = (entries = [], limit = 3) =>
  [...entries]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);

const latestRecord = computed(() => records.value[0] || null);
const latestStats = computed(() => latestRecord.value?.stats || {});

const topInstrumentEntries = computed(() =>
  sortEntries(Object.entries(latestStats.value.by_instrument || {}), 3)
);

const topAreaEntries = computed(() =>
  sortEntries(Object.entries(latestStats.value.by_area || {}), 4)
);

const responseTypeMap = {
  qa: '问答',
  stats: '统计',
  both: '问答 + 统计',
};

const retrievalModeMap = {
  mix: '混合检索',
  local: '知识库检索',
  global: '知识图谱检索',
  llm: '纯模型回答',
};

const topInstrumentChips = computed(() => {
  if (!topInstrumentEntries.value.length) return [{ label: '暂无仪器统计' }];
  return topInstrumentEntries.value.map(([name, count]) => ({
    label: `${name} ${count}`,
  }));
});

const topAreaChips = computed(() => {
  if (!topAreaEntries.value.length) return [{ label: '暂无区域统计' }];
  return topAreaEntries.value.map(([name, count]) => ({
    label: `${name} ${count}`,
  }));
});

const overviewCards = computed(() => {
  const recordCount = records.value.length;
  const latestInstrument = topInstrumentEntries.value[0];
  const latestArea = topAreaEntries.value[0];
  const severePoint = latestStats.value.most_severe?.pointName;

  return [
    {
      label: '调用档案',
      value: `${recordCount} 条`,
      note: recordCount ? '已记录外部系统调用结果' : '等待首条调用记录',
    },
    {
      label: '最新异常测点',
      value: `${latestStats.value.total_count || 0} 个`,
      note: latestRecord.value ? '基于最近一次调用结果' : '暂无统计数据',
    },
    {
      label: '主要异常类型',
      value: latestInstrument ? latestInstrument[0] : '-',
      note: latestInstrument ? `${latestInstrument[1]} 个异常测点` : '暂无类型分布',
    },
    {
      label: '重点关注测点',
      value: severePoint || '-',
      note: latestArea ? `主要异常区域 ${latestArea[0]}` : '暂无区域统计',
    },
  ];
});

const buildRecordFootnotes = (item) => {
  const stats = item?.stats || {};
  const instrumentEntry = sortEntries(Object.entries(stats.by_instrument || {}), 1)[0];
  const areaEntry = sortEntries(Object.entries(stats.by_area || {}), 1)[0];
  const notes = [];

  if (stats.total_count) {
    notes.push(`异常测点 ${stats.total_count} 个`);
  }
  if (instrumentEntry) {
    notes.push(`主要类型 ${instrumentEntry[0]} ${instrumentEntry[1]} 个`);
  }
  if (areaEntry) {
    notes.push(`主要区域 ${areaEntry[0]}`);
  }
  if (stats.most_severe?.pointName) {
    notes.push(`优先测点 ${stats.most_severe.pointName}`);
  }
  if (item?.response_type) {
    notes.push(`返回模式 ${getResponseTypeLabel(item.response_type)}`);
  }
  if (item?.retrieval?.retrieval_mode) {
    notes.push(`检索方式 ${getRetrievalModeLabel(item.retrieval.retrieval_mode)}`);
  }

  return notes;
};

const getResponseTypeLabel = (responseType) => responseTypeMap[responseType] || '问答 + 统计';

const getRetrievalModeLabel = (mode) => retrievalModeMap[mode] || '未知模式';

const renderAnswer = (content) => {
  try {
    return marked.parse(content || '');
  } catch (error) {
    console.warn('异常问答 Markdown 渲染失败:', error);
    return String(content || '').replace(/\n/g, '<br>');
  }
};

const loadRecords = async (limit = 50) => {
  loading.value = true;
  try {
    const res = await damExceptionQaApi.getRecords(limit);
    records.value = res.records || [];
  } catch (error) {
    console.error('加载异常问答记录失败:', error);
    message.error(error.message || '加载异常问答记录失败');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadRecords();
});
</script>

<style lang="less" scoped>
.exception-qa-view {
  min-height: 100%;
  padding: 28px 28px 32px;
  color: #f6fbff;
  background:
    radial-gradient(circle at top right, rgba(0, 212, 255, 0.14), transparent 26%),
    radial-gradient(circle at left 20%, rgba(13, 148, 136, 0.12), transparent 24%);
}

.hero-panel,
.overview-card,
.intel-panel,
.record-card {
  border: 1px solid rgba(103, 232, 249, 0.14);
  background: linear-gradient(180deg, rgba(5, 35, 82, 0.9), rgba(4, 24, 60, 0.92));
  box-shadow:
    0 18px 40px rgba(0, 0, 0, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(16px);
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px;
  border-radius: 24px;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    inset: auto -8% -40% auto;
    width: 340px;
    height: 340px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(34, 211, 238, 0.24), transparent 68%);
    pointer-events: none;
  }
}

.hero-copy {
  max-width: 760px;

  h2 {
    margin: 8px 0 14px;
    font-size: 40px;
    line-height: 1.05;
    font-weight: 800;
    letter-spacing: 0.02em;
  }

  p {
    max-width: 680px;
    color: rgba(222, 242, 255, 0.72);
    font-size: 15px;
    line-height: 1.85;
  }
}

.hero-kicker,
.section-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #67e8f9;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.hero-actions {
  display: grid;
  grid-template-columns: minmax(0, 220px) minmax(0, 160px) auto;
  align-items: start;
  gap: 14px;
  z-index: 1;
}

.signal-card {
  min-width: 220px;
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(0, 20, 48, 0.62), rgba(0, 9, 27, 0.5));
  border: 1px solid rgba(103, 232, 249, 0.2);

  strong {
    display: block;
    margin-top: 6px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
}

.hero-mini-metrics {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  min-width: 150px;
}

.hero-mini-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(1, 16, 39, 0.74), rgba(3, 21, 54, 0.54));
  border: 1px solid rgba(255, 255, 255, 0.08);

  span {
    display: block;
    color: rgba(173, 216, 255, 0.58);
    font-size: 12px;
  }

  strong {
    display: block;
    margin-top: 8px;
    font-size: 22px;
    font-weight: 800;
  }
}

.signal-label,
.signal-sub {
  display: block;
}

.signal-label {
  color: rgba(173, 216, 255, 0.62);
  font-size: 12px;
}

.signal-sub {
  margin-top: 8px;
  color: #7dd3fc;
  font-size: 12px;
}

.refresh-btn {
  height: 48px;
  padding: 0 18px;
  border-radius: 14px;
  border: 1px solid rgba(34, 211, 238, 0.34);
  background: linear-gradient(135deg, rgba(8, 145, 178, 0.28), rgba(14, 116, 144, 0.12));
  color: #d9fbff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    border-color: rgba(103, 232, 249, 0.65);
    box-shadow: 0 14px 28px rgba(8, 145, 178, 0.18);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.overview-card {
  min-height: 140px;
  padding: 18px 18px 20px;
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;

  &::before {
    content: '';
    position: absolute;
    inset: 0 auto auto 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, #22d3ee, rgba(34, 211, 238, 0));
  }

  strong {
    display: block;
    margin-top: 18px;
    font-size: 28px;
    line-height: 1.1;
    font-weight: 800;
    word-break: break-word;
  }
}

.overview-label {
  display: block;
  color: rgba(191, 230, 255, 0.62);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.overview-note {
  display: block;
  margin-top: 12px;
  color: rgba(221, 240, 255, 0.58);
  font-size: 12px;
  line-height: 1.6;
}

.dashboard-shell {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
  align-items: start;
}

.intel-panel {
  position: sticky;
  top: 18px;
  border-radius: 24px;
  padding: 20px;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  span {
    color: rgba(191, 230, 255, 0.72);
    font-size: 13px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  strong {
    color: #67e8f9;
    font-size: 13px;
    font-weight: 700;
  }
}

.latest-brief {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 18px;
}

.brief-block {
  padding: 14px 14px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);

  &:first-of-type {
    padding-top: 0;
    border-top: none;
  }

  p {
    margin-top: 8px;
    color: rgba(239, 249, 255, 0.92);
    line-height: 1.8;
  }
}

.brief-label {
  color: rgba(173, 216, 255, 0.58);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.brief-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 0 14px;
}

.brief-metric {
  padding: 14px;
  border-radius: 16px;
  background: rgba(5, 18, 44, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);

  span {
    display: block;
    color: rgba(173, 216, 255, 0.54);
    font-size: 12px;
  }

  strong {
    display: block;
    margin-top: 8px;
    font-size: 15px;
    font-weight: 700;
    word-break: break-word;
  }
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.info-chip,
.mini-chip,
.foot-chip,
.source-tag,
.fallback-tag,
.mode-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  white-space: nowrap;
}

.info-chip {
  padding: 6px 10px;
  background: rgba(14, 116, 144, 0.18);
  border: 1px solid rgba(103, 232, 249, 0.2);
  color: #dbfbff;
  font-size: 12px;

  &.area {
    background: rgba(15, 118, 110, 0.14);
    border-color: rgba(45, 212, 191, 0.2);
  }
}

.panel-empty {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(5, 18, 44, 0.5);
  color: rgba(222, 242, 255, 0.62);
  line-height: 1.8;
}

.records-panel {
  min-width: 0;
}

.records-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  margin-bottom: 12px;

  h3 {
    margin-top: 6px;
    font-size: 24px;
    font-weight: 800;
  }
}

.record-count {
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(222, 242, 255, 0.76);
  font-size: 13px;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.record-item {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: 14px;
  opacity: 0;
  transform: translateY(10px);
  animation: record-in 0.55s ease forwards;
}

.record-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 14px;
}

.rail-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: radial-gradient(circle, #67e8f9 0%, #0ea5e9 72%);
  box-shadow: 0 0 0 6px rgba(34, 211, 238, 0.08);
}

.rail-line {
  flex: 1;
  width: 1px;
  margin-top: 8px;
  background: linear-gradient(180deg, rgba(103, 232, 249, 0.34), rgba(103, 232, 249, 0));
}

.record-item:last-child .rail-line {
  display: none;
}

.record-card {
  border-radius: 24px;
  padding: 18px 18px 16px;
  overflow: hidden;
}

.record-meta {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 18px;
}

.meta-main {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.record-time {
  font-size: 14px;
  font-weight: 700;
  color: #f2fbff;
}

.record-relative {
  color: rgba(173, 216, 255, 0.62);
  font-size: 12px;
}

.meta-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.source-tag {
  padding: 7px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(227, 242, 253, 0.78);
  font-size: 12px;
}

.fallback-tag {
  padding: 7px 12px;
  background: rgba(234, 179, 8, 0.14);
  border: 1px solid rgba(250, 204, 21, 0.32);
  color: #fde68a;
  font-size: 12px;
}

.mode-tag {
  padding: 7px 12px;
  background: rgba(34, 211, 238, 0.14);
  border: 1px solid rgba(103, 232, 249, 0.28);
  color: #bff8ff;
  font-size: 12px;
}

.question-block,
.answer-block,
.stats-summary-block {
  margin-top: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.question-block {
  background: linear-gradient(180deg, rgba(6, 22, 54, 0.86), rgba(8, 30, 74, 0.6));

  p {
    margin-top: 8px;
    color: #effbff;
    font-size: 16px;
    line-height: 1.8;
    font-weight: 600;
  }
}

.answer-block {
  background: linear-gradient(180deg, rgba(2, 15, 40, 0.82), rgba(5, 25, 61, 0.68));
}

.stats-summary-block {
  background: linear-gradient(180deg, rgba(7, 31, 54, 0.82), rgba(4, 39, 58, 0.62));
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.analysis-panel {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.problem-panel {
  background: linear-gradient(180deg, rgba(58, 17, 43, 0.52), rgba(43, 16, 55, 0.38));
}

.suggestion-panel {
  background: linear-gradient(180deg, rgba(9, 48, 55, 0.58), rgba(6, 36, 47, 0.42));
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.panel-counter {
  color: rgba(191, 230, 255, 0.66);
  font-size: 12px;
}

.insight-list {
  margin: 0;
  padding-left: 1.2rem;
  color: rgba(236, 248, 255, 0.9);
  line-height: 1.8;

  li + li {
    margin-top: 0.55rem;
  }

  &.ordered {
    padding-left: 1.35rem;
  }
}

.answer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.block-label {
  color: #7dd3fc;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.answer-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mini-chip,
.foot-chip {
  padding: 6px 10px;
  border: 1px solid rgba(103, 232, 249, 0.16);
  background: rgba(14, 116, 144, 0.12);
  color: rgba(227, 249, 255, 0.84);
  font-size: 12px;
}

.subtle-chip {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
}

.record-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.state-tip {
  padding: 42px 28px;
  border-radius: 24px;
  border: 1px dashed rgba(103, 232, 249, 0.18);
  background: rgba(4, 21, 52, 0.56);
  color: rgba(221, 240, 255, 0.62);
  text-align: center;
  font-size: 14px;

  &.empty {
    color: rgba(173, 216, 255, 0.56);
  }
}

.scrollbar-custom::-webkit-scrollbar {
  width: 8px;
}

.scrollbar-custom::-webkit-scrollbar-thumb {
  background: rgba(103, 232, 249, 0.16);
  border-radius: 999px;
}

.answer-rich-text {
  color: rgba(240, 249, 255, 0.9);
  font-size: 14px;
  line-height: 1.9;

  :deep(*) {
    max-width: 100%;
  }
}

.summary-rich-text {
  font-size: 13px;
  line-height: 1.8;
}

:deep(.answer-rich-text > *) {
  position: static;
}

:deep(.answer-rich-text) {
  color: rgba(240, 249, 255, 0.9);
  font-size: 14px;
  line-height: 1.9;
}

:deep(.answer-rich-text h1),
:deep(.answer-rich-text h2) {
  margin-top: 1.2em;
  margin-bottom: 0.6em;
  color: #f6fbff;
  font-size: 1.28rem;
}

:deep(.answer-rich-text h3),
:deep(.answer-rich-text h4) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  color: #dff7ff;
  font-size: 1.08rem;
}

:deep(.answer-rich-text p),
:deep(.answer-rich-text li) {
  color: rgba(236, 248, 255, 0.88);
}

:deep(.answer-rich-text p + p) {
  margin-top: 0.85em;
}

:deep(.answer-rich-text strong) {
  color: #7dd3fc;
  font-weight: 700;
}

:deep(.answer-rich-text ul),
:deep(.answer-rich-text ol) {
  padding-left: 1.5rem;
}

:deep(.answer-rich-text ul li + li),
:deep(.answer-rich-text ol li + li) {
  margin-top: 0.35em;
}

:deep(.answer-rich-text li::marker) {
  color: #22d3ee;
}

:deep(.answer-rich-text hr) {
  margin: 1.4em 0;
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.answer-rich-text table) {
  display: table;
  width: 100%;
  margin: 1.4em 0;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid rgba(103, 232, 249, 0.16);
}

:deep(.answer-rich-text th) {
  background: rgba(14, 116, 144, 0.22);
  color: #effbff;
  font-weight: 700;
}

:deep(.answer-rich-text th),
:deep(.answer-rich-text td) {
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  text-align: left;
}

:deep(.answer-rich-text tr:last-child td) {
  border-bottom: none;
}

:deep(.answer-rich-text code) {
  padding: 0.15rem 0.38rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  color: #d9fbff;
}

:deep(.answer-rich-text pre) {
  margin: 1em 0;
  overflow-x: auto;
}

:deep(.answer-rich-text pre code) {
  display: block;
  padding: 14px;
  border-radius: 12px;
  background: rgba(1, 10, 26, 0.9);
}

@keyframes record-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1280px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-shell {
    grid-template-columns: 1fr;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .intel-panel {
    position: static;
  }
}

@media (max-width: 900px) {
  .exception-qa-view {
    padding: 18px 16px 24px;
  }

  .hero-panel {
    flex-direction: column;
    padding: 22px 20px;
  }

  .hero-copy h2 {
    font-size: 30px;
  }

  .hero-actions {
    grid-template-columns: 1fr;
  }

  .signal-card {
    width: 100%;
  }

  .hero-mini-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .records-head {
    align-items: start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .overview-grid,
  .brief-grid,
  .hero-mini-metrics {
    grid-template-columns: 1fr;
  }

  .record-item {
    grid-template-columns: 1fr;
  }

  .record-rail {
    display: none;
  }

  .record-card {
    padding: 16px 14px 14px;
    border-radius: 20px;
  }

  .question-block,
  .answer-block,
  .stats-summary-block,
  .analysis-panel {
    padding: 14px;
  }

  .answer-head,
  .record-meta {
    flex-direction: column;
    align-items: start;
  }

  .meta-tags {
    justify-content: flex-start;
  }
}
</style>
