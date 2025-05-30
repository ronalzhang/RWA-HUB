/**
 * IP访问统计模块
 */
class IPStatsManager {
    constructor() {
        this.charts = {};
        this.currentPeriod = 'hourly';
        this.isLoading = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
    }

    // 获取钱包地址的方法（与dashboard.html中的方法一致）
    getWalletAddress() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('eth_address');
    }

    // 创建带认证头的fetch请求（与dashboard.html中的方法一致）
    authFetch(url, options = {}) {
        const walletAddress = this.getWalletAddress();
        return fetch(url, {
            ...options,
            headers: {
                'X-Wallet-Address': walletAddress,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
    }

    bindEvents() {
        // 标签页切换事件 - 适配新的按钮结构
        document.querySelectorAll('.ip-stats-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const period = tab.dataset.period;
                this.switchTab(period);
            });
        });

        // 刷新按钮事件
        const refreshBtn = document.getElementById('refreshIPStats');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshCurrentData();
            });
        }

        // 导出按钮事件
        const exportBtn = document.getElementById('exportIPStats');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportData();
            });
        }
    }

    switchTab(period) {
        // 更新按钮状态
        document.querySelectorAll('.ip-stats-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = document.querySelector(`[data-period="${period}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
        }

        // 更新内容区域
        document.querySelectorAll('.ip-stats-content').forEach(content => {
            content.style.display = 'none';
        });
        const activeContent = document.getElementById(`ip-stats-${period}`);
        if (activeContent) {
            activeContent.style.display = 'block';
        }

        this.currentPeriod = period;
        this.loadData(period);
    }

    async loadInitialData() {
        // 加载总体统计
        await this.loadSummaryStats();
        // 加载默认标签页数据
        await this.loadData('hourly');
    }

    async loadSummaryStats() {
        try {
            const response = await this.authFetch('/admin/api/ip-stats/summary');
            const result = await response.json();

            if (result.success) {
                this.updateSummaryDisplay(result.data);
            } else {
                console.error('加载总体统计失败:', result.error);
            }
        } catch (error) {
            console.error('加载总体统计出错:', error);
        }
    }

    updateSummaryDisplay(data) {
        // 更新总体统计显示
        const elements = {
            'total-visits': data.total_visits,
            'total-unique-ips': data.total_unique_ips,
            'today-visits': data.today_visits,
            'today-unique-ips': data.today_unique_ips,
            'yesterday-visits': data.yesterday_visits
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = this.formatNumber(value);
            }
        });

        // 更新增长率
        const growthElement = document.getElementById('growth-rate');
        if (growthElement) {
            const rate = data.growth_rate || 0;
            growthElement.textContent = `${rate >= 0 ? '+' : ''}${rate.toFixed(1)}%`;
            growthElement.className = `growth-rate ${rate >= 0 ? 'positive' : 'negative'}`;
        }
    }

    async loadData(period) {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(period);

        try {
            const response = await this.authFetch(`/admin/api/ip-stats/${period}`);
            const result = await response.json();

            if (result.success) {
                this.renderChart(period, result.data);
                console.log(`${period}数据加载成功:`, result.data);
            } else {
                console.error(`加载${period}数据失败:`, result.error);
                this.showError(period, result.error);
            }
        } catch (error) {
            console.error(`加载${period}数据出错:`, error);
            this.showError(period, error.message);
        } finally {
            this.isLoading = false;
            this.hideLoading(period);
        }
    }

    renderChart(period, data) {
        const canvasId = `chart-${period}`;
        let canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas ${canvasId} not found`);
            return;
        }

        // 彻底销毁现有图表
        if (this.charts[period]) {
            try {
                this.charts[period].destroy();
                this.charts[period] = null;
                delete this.charts[period];
            } catch (e) {
                console.warn('销毁图表时出错:', e);
            }
        }

        // 获取容器
        const container = canvas.parentElement;
        
        // 完全重新创建canvas元素
        const newCanvas = document.createElement('canvas');
        newCanvas.id = canvasId;
        newCanvas.style.maxHeight = '100%';
        newCanvas.style.maxWidth = '100%';
        
        // 替换旧canvas
        container.removeChild(canvas);
        container.appendChild(newCanvas);
        
        // 获取新的canvas上下文
        const ctx = newCanvas.getContext('2d');
        
        // 创建新图表
        try {
            this.charts[period] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: '访问次数',
                            data: data.visit_data,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#3b82f6',
                            pointBorderColor: '#3b82f6',
                            pointRadius: 4,
                            pointHoverRadius: 6
                        },
                        {
                            label: '独立IP',
                            data: data.unique_ip_data,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: '#10b981',
                            pointBorderColor: '#10b981',
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: data.period || '访问统计',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            color: '#374151',
                            padding: {
                                bottom: 20
                            }
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#6b7280',
                                usePointStyle: true,
                                padding: 20
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#6b7280'
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: '#6b7280',
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    elements: {
                        point: {
                            radius: 3,
                            hoverRadius: 6
                        }
                    }
                }
            });
            
            console.log(`图表 ${period} 创建成功`);
        } catch (error) {
            console.error('创建图表失败:', error);
            this.showError(period, '图表创建失败: ' + error.message);
        }
    }

    showLoading(period) {
        const container = document.getElementById(`ip-stats-${period}`);
        if (container) {
            const loadingDiv = container.querySelector('.loading-indicator') || 
                document.createElement('div');
            loadingDiv.className = 'loading-indicator text-center p-4';
            loadingDiv.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">加载中...</span>
                </div>
                <p class="mt-2">正在加载数据...</p>
            `;
            if (!container.querySelector('.loading-indicator')) {
                container.appendChild(loadingDiv);
            }
        }
    }

    hideLoading(period) {
        const container = document.getElementById(`ip-stats-${period}`);
        if (container) {
            const loadingDiv = container.querySelector('.loading-indicator');
            if (loadingDiv) {
                loadingDiv.remove();
            }
        }
    }

    showError(period, message) {
        const container = document.getElementById(`ip-stats-${period}`);
        if (container) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger';
            errorDiv.innerHTML = `
                <h6>加载失败</h6>
                <p>${message}</p>
                <button class="btn btn-sm btn-outline-danger" onclick="ipStatsManager.loadData('${period}')">
                    重试
                </button>
            `;
            container.appendChild(errorDiv);
        }
    }

    async refreshCurrentData() {
        await this.loadSummaryStats();
        await this.loadData(this.currentPeriod);
    }

    async exportData() {
        try {
            const response = await this.authFetch(`/admin/api/ip-stats/${this.currentPeriod}`);
            const result = await response.json();

            if (result.success) {
                const data = result.data;
                const csvContent = this.generateCSV(data);
                this.downloadCSV(csvContent, `ip-stats-${this.currentPeriod}-${new Date().toISOString().split('T')[0]}.csv`);
            }
        } catch (error) {
            console.error('导出数据失败:', error);
            alert('导出数据失败，请重试');
        }
    }

    generateCSV(data) {
        const headers = ['时间', '访问次数', '独立IP数'];
        const rows = [headers.join(',')];

        for (let i = 0; i < data.labels.length; i++) {
            const row = [
                data.labels[i],
                data.visit_data[i],
                data.unique_ip_data[i]
            ];
            rows.push(row.join(','));
        }

        return rows.join('\n');
    }

    downloadCSV(content, filename) {
        const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return num.toLocaleString();
    }
}

// 全局实例
let ipStatsManager;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('ip-stats-container')) {
        ipStatsManager = new IPStatsManager();
    }
}); 