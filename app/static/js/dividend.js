/**
 * dividend.js - 资产分红功能模块
 * 版本：1.0.0
 * 
 * 此文件整合了之前dividend_fix.js的功能
 */

(function() {
  // 避免重复初始化
  if (window.dividendModuleInitialized) {
    return;
  }
  window.dividendModuleInitialized = true;
  
  console.log('初始化分红功能模块 v1.0.0');
  
  // 获取当前钱包地址
  function getWalletAddress() {
    return localStorage.getItem('walletAddress') || '';
  }
  
  // 获取我的分红历史
  window.getMyDividendHistory = function() {
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
      console.warn('获取分红历史: 钱包未连接');
      showMessage('请先连接钱包查看分红记录', 'warning');
      return Promise.reject(new Error('钱包未连接'));
    }
    
    return fetch(`/api/dividends/history?wallet_address=${encodeURIComponent(walletAddress)}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
      });
  };
  
  // 领取分红
  window.claimDividend = function(recordId) {
    if (!recordId) {
      console.error('领取分红: 记录ID未提供');
      return Promise.reject(new Error('记录ID未提供'));
    }
    
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
      console.warn('领取分红: 钱包未连接');
      showMessage('请先连接钱包领取分红', 'warning');
      return Promise.reject(new Error('钱包未连接'));
    }
    
    const claimData = {
      record_id: recordId,
      wallet_address: walletAddress
    };
    
    return fetch('/api/dividends/claim', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(claimData)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      
      // 检查是否需要签名
      if (data.requires_signature && typeof signAndConfirmTransaction === 'function') {
        return signAndConfirmTransaction(data.transaction_data)
          .then(signatureData => {
            // 确认领取
            return confirmClaim(data.claim_id, signatureData.signature);
          });
      } else {
        // 无需签名，直接确认领取
        return confirmClaim(data.claim_id);
      }
    });
  };
  
  // 确认领取分红
  function confirmClaim(claimId, signature = null) {
    const confirmData = { claim_id: claimId };
    if (signature) {
      confirmData.signature = signature;
    }
    
    return fetch('/api/dividends/confirm_claim', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(confirmData)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      return data;
    });
  }
  
  // 显示消息
  function showMessage(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    } else {
      alert(message);
    }
  }
  
  // 初始化分红表格
  window.initDividendTable = function() {
    const tableContainer = document.getElementById('dividendHistoryTable');
    if (!tableContainer) {
      return;
    }
    
    // 获取并显示分红历史
    getMyDividendHistory()
      .then(data => {
        renderDividendTable(data.records || []);
      })
      .catch(error => {
        console.error('获取分红历史失败:', error);
        showMessage(`获取分红历史失败: ${error.message}`, 'error');
        
        // 显示空表格
        renderDividendTable([]);
      });
  };
  
  // 渲染分红表格
  function renderDividendTable(records) {
    const tableContainer = document.getElementById('dividendHistoryTable');
    if (!tableContainer) {
      return;
    }
    
    if (records.length === 0) {
      tableContainer.innerHTML = '<div class="alert alert-info">暂无分红记录</div>';
      return;
    }
    
    // 创建表格
    let tableHtml = `
      <table class="table table-striped">
        <thead>
          <tr>
            <th>资产</th>
            <th>分红金额</th>
            <th>创建时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
    `;
    
    // 添加记录行
    records.forEach(record => {
      const status = record.claimed ? '已领取' : '待领取';
      const buttonHtml = record.claimed ? 
        '<button class="btn btn-sm btn-secondary" disabled>已领取</button>' : 
        `<button class="btn btn-sm btn-primary claim-dividend" data-record-id="${record.id}">领取</button>`;
      
      tableHtml += `
        <tr>
          <td>${record.asset_name || record.asset_id || '-'}</td>
          <td>${record.amount || '0.00'}</td>
          <td>${new Date(record.created_at).toLocaleString()}</td>
          <td>${status}</td>
          <td>${buttonHtml}</td>
        </tr>
      `;
    });
    
    tableHtml += `
        </tbody>
      </table>
    `;
    
    // 更新表格内容
    tableContainer.innerHTML = tableHtml;
    
    // 绑定领取按钮事件
    const claimButtons = tableContainer.querySelectorAll('.claim-dividend');
    claimButtons.forEach(button => {
      button.addEventListener('click', function() {
        const recordId = this.getAttribute('data-record-id');
        if (!recordId) {
          return;
        }
        
        // 禁用按钮，防止重复点击
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 处理中...';
        
        // 执行领取
        claimDividend(recordId)
          .then(result => {
            showMessage('分红领取成功！', 'success');
            // 刷新表格
            setTimeout(() => {
              initDividendTable();
            }, 1500);
          })
          .catch(error => {
            console.error('领取分红失败:', error);
            showMessage(`领取失败: ${error.message}`, 'error');
            
            // 恢复按钮状态
            this.disabled = false;
            this.innerHTML = '领取';
          });
      });
    });
  }
  
  // 初始化
  document.addEventListener('DOMContentLoaded', function() {
    // 如果存在分红表格，初始化它
    if (document.getElementById('dividendHistoryTable')) {
      initDividendTable();
    }
  });
  
})(); 