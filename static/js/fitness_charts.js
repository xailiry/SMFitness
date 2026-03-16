/**
 * Shared Chart.js configuration and helper functions for SMFitness.
 */

const getIsDark = () => document.documentElement.classList.contains('dark');
const formatNumber = (num) => Math.round(num * 100) / 100;

const initChartDefaults = () => {
    const isDark = getIsDark();
    Chart.defaults.font.family = 'Outfit, Inter, sans-serif';
    Chart.defaults.color = isDark ? '#9ca3af' : '#64748b';
    return isDark ? '#334155' : '#f1f5f9'; // Returns gridColor
};

const CHART_COLORS = [
    '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#f97316', '#6366f1'
];

const CHART_GRADIENTS = [
    ['#3b82f6', '#2563eb'], ['#10b981', '#059669'], ['#8b5cf6', '#7c3aed'], 
    ['#f59e0b', '#d97706'], ['#ef4444', '#dc2626'], ['#06b6d4', '#0891b2'], 
    ['#ec4899', '#db2777'], ['#f97316', '#ea580c'], ['#6366f1', '#4f46e5']
];

function getWeekString(dateStr) {
    const d = new Date(dateStr);
    const day = d.getDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
    const weekNo = Math.ceil(( ( (d - yearStart) / 86400000) + 1)/7);
    return `${d.getUTCFullYear()}-W${weekNo < 10 ? '0'+weekNo : weekNo}`;
}

function getReadableWeek(dateStr, weekNum) {
    const d = new Date(dateStr);
    const day = d.getDay() || 7;
    const start = new Date(d);
    start.setDate(d.getDate() - day + 1);
    const options = { month: 'short', day: 'numeric' };
    return `Нед ${weekNum} (${start.toLocaleDateString('ru-RU', options)})`;
}

/**
 * Common tooltip configuration to avoid duplication.
 */
function getCommonTooltipConfig(isDark) {
    return {
        backgroundColor: isDark ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)',
        titleColor: isDark ? '#f8fafc' : '#1e293b',
        bodyColor: isDark ? '#94a3b8' : '#64748b',
        borderColor: isDark ? '#334155' : '#e2e8f0',
        borderWidth: 1,
        padding: 12,
        boxPadding: 6,
        usePointStyle: true,
        titleFont: { size: 14, weight: 'bold', family: 'Outfit' },
        bodyFont: { size: 13, family: 'Outfit' }
    };
}
