/**
 * Ant Design Vue 主题配置
 * 用于 ConfigProvider 组件的 theme 属性
 */
import { theme } from 'ant-design-vue';

export const themeConfig = {
    algorithm: theme.darkAlgorithm,
    token: {
        // 主色调 - 科技蓝 (Electric Cyan)
        colorPrimary: '#06b6d4',
        colorLink: '#06b6d4',
        colorLinkHover: '#22d3ee',

        // 背景色 - 深邃海军蓝
        colorBgBase: '#020617',
        colorBgContainer: 'rgba(15, 23, 42, 0.6)', // 更透明的容器
        colorBgElevated: '#0f172a',

        // 文本色
        colorText: '#f8fafc',
        colorTextSecondary: '#94a3b8',
        colorTextTertiary: '#64748b',
        colorTextQuaternary: '#475569',

        // 边框色
        colorBorder: 'rgba(255, 255, 255, 0.1)',
        colorBorderSecondary: 'rgba(255, 255, 255, 0.05)',

        // 圆角
        borderRadius: 12,
        borderRadiusLG: 16,
        borderRadiusSM: 6,

        // 字体
        fontFamily: "'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif",
        fontSize: 14,
    },
    components: {
        Button: {
            borderRadius: 8,
            controlHeight: 38,
            primaryShadow: '0 0 20px rgba(6, 182, 212, 0.4)',
        },
        Input: {
            borderRadius: 8,
            colorBgContainer: 'rgba(15, 23, 42, 0.4)',
            activeBorderColor: '#06b6d4',
        },
        Select: {
            borderRadius: 8,
            colorBgContainer: 'rgba(15, 23, 42, 0.4)',
        },
        Card: {
            borderRadius: 16,
            colorBgContainer: 'rgba(30, 41, 59, 0.3)',
            colorBorderSecondary: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(12px)', // 玻璃拟态
        },
        Modal: {
            borderRadius: 20,
            colorBgElevated: '#1e293b',
            headerBg: 'transparent',
            contentBg: 'rgba(30, 41, 59, 0.8)',
        },
        Table: {
            borderRadius: 12,
            colorBgContainer: 'transparent',
            headerBg: 'rgba(30, 41, 59, 0.4)',
            rowHoverBg: 'rgba(6, 182, 212, 0.1)',
        },
        Menu: {
            itemBorderRadius: 8,
            itemBg: 'transparent',
            itemSelectedBg: 'rgba(6, 182, 212, 0.2)',
            itemSelectedColor: '#22d3ee',
            itemHoverBg: 'rgba(255, 255, 255, 0.05)',
        },
    },
};

export default themeConfig;
