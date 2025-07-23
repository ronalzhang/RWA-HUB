// Asset Detail页面的JavaScript功能

// 复制资产链接到剪贴板
function copyAssetLink() {
  const linkInput = document.getElementById('asset-link');
  if (!linkInput) return;
  
  linkInput.select();
  document.execCommand('copy');
  
  // 显示复制成功提示
  const copyBtn = document.getElementById('copy-link-btn');
  if (!copyBtn) return;
  
  const originalHTML = copyBtn.innerHTML;
  copyBtn.innerHTML = '<i class="bi bi-check2"></i>';
  copyBtn.classList.add('btn-success');
  copyBtn.classList.remove('btn-outline-primary');
  
  setTimeout(function() {
    copyBtn.innerHTML = originalHTML;
    copyBtn.classList.remove('btn-success');
    copyBtn.classList.add('btn-outline-primary');
  }, 2000);
}

// 分享资产到社交媒体
function shareAsset(platform) {
  const linkInput = document.getElementById('asset-link');
  if (!linkInput) return;
  
  const url = linkInput.value;
  const assetName = window.assetData ? window.assetData.name : '资产';
  const assetSymbol = window.assetData ? window.assetData.token_symbol : '';
  const title = '查看资产: ' + assetName + ' (' + assetSymbol + ')';
  
  let shareUrl;
  
  switch(platform) {
    case 'wechat':
      // 微信通常使用二维码分享，这里可以打开一个显示二维码的模态框
      alert('Please use WeChat to scan the QR code for sharing');
      return;
    case 'weibo':
      shareUrl = 'http://service.weibo.com/share/share.php?url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(title);
      break;
    case 'twitter':
      shareUrl = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
      break;
    default:
      shareUrl = url;
  }
  
  window.open(shareUrl, '_blank');
}

// 加载总分红数据
function loadTotalDividends() {
  const dividendsTable = document.getElementById('dividendsTable');
  if (!dividendsTable) {
    console.warn('分红历史表格元素不存在，跳过加载总分红');
    return;
  }
  
  if (!window.assetData || !window.assetData.token_symbol) {
    console.error('资产数据不存在，无法加载分红');
    return;
  }
  
  fetch('/api/assets/' + window.assetData.token_symbol + '/dividends/total')
    .then(function(response) {
      if (!response.ok) {
        throw new Error('获取总分红数据失败');
      }
      return response.json();
    })
    .then(function(data) {
      const totalDividendsElement = document.getElementById('totalDividendsDistributed');
      if (totalDividendsElement) {
        var amount = data.total_amount || '0';
        totalDividendsElement.textContent = amount + ' USDC';
      } else {
        console.warn('找不到显示总分红的元素');
      }
    })
    .catch(function(error) {
      console.error('加载总分红数据时出错:', error);
    });
}

// 初始化页面
function initAssetDetailPage() {
  // 尝试执行refreshAssetInfo如果它存在
  if (typeof refreshAssetInfo === 'function') {
    refreshAssetInfo();
  } else {
    // 如果不存在，使用安全的刷新方法
    console.warn('refreshAssetInfo not defined, using safe refresh method');
    if (typeof safeRefreshAssetInfo === 'function') {
      safeRefreshAssetInfo();
    }
  }
  
  // 初始化交易表单（如果存在）
  if (typeof setupTradeForm === 'function') {
    setupTradeForm();
  }
  
  // 加载总分红
  loadTotalDividends();
  
  // 加载交易历史（如果函数存在）
  if (typeof loadTransactionHistory === 'function') {
    loadTransactionHistory(1);
  }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initAssetDetailPage); 