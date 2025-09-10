/**
 * 管理员状态检查脚本
 * 版本: 1.0.0
 * 功能: 检查连接的钱包是否为管理员，并显示/隐藏后台管理入口
 */

(function() {
    'use strict';
    
    let isAdminUser = false;
    let currentWalletAddress = null;
    
    // 管理员地址列表（从配置文件同步）
    const ADMIN_ADDRESSES = [
        '6UrwhN2rqQvo2tBfc9FZCdUbt9JLs3BJiEm7pv4NM41b'
    ];
    
    /**
     * 检查管理员状态
     */
    async function checkAdminStatus(walletAddress) {
        if (!walletAddress) {
            console.log('管理员检查: 钱包地址为空');
            updateAdminUI(false);
            return false;
        }
        
        console.log('检查管理员状态:', walletAddress);
        currentWalletAddress = walletAddress;
        
        try {
            // 方法1: 直接检查配置中的管理员地址
            const isConfigAdmin = ADMIN_ADDRESSES.includes(walletAddress);
            if (isConfigAdmin) {
                console.log('配置验证: 是管理员');
                isAdminUser = true;
                updateAdminUI(true);
                return true;
            }
            
            // 方法2: 调用后端API验证
            const response = await fetch('/api/admin/check', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Eth-Address': walletAddress
                },
                body: JSON.stringify({
                    wallet_address: walletAddress
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                isAdminUser = data.is_admin === true;
                console.log('API验证结果:', isAdminUser);
                updateAdminUI(isAdminUser);
                return isAdminUser;
            } else {
                console.log('API验证失败，使用配置验证结果');
                isAdminUser = isConfigAdmin;
                updateAdminUI(isAdminUser);
                return isAdminUser;
            }
            
        } catch (error) {
            console.error('检查管理员状态出错:', error);
            // 如果API调用失败，使用配置验证
            const isConfigAdmin = ADMIN_ADDRESSES.includes(walletAddress);
            isAdminUser = isConfigAdmin;
            updateAdminUI(isAdminUser);
            return isAdminUser;
        }
    }
    
    /**
     * 更新管理员UI显示
     */
    function updateAdminUI(isAdmin) {
        console.log('更新管理员UI:', isAdmin);
        
        // 查找后台管理链接
        const adminNavLink = document.getElementById('adminNavLink');
        const adminButton = document.querySelector('.admin-button');
        const adminMenuItem = document.querySelector('.admin-menu-item');
        
        // 显示/隐藏后台管理入口
        if (adminNavLink) {
            adminNavLink.style.display = isAdmin ? 'block' : 'none';
            console.log('adminNavLink显示状态:', isAdmin ? '显示' : '隐藏');
        }
        
        if (adminButton) {
            adminButton.style.display = isAdmin ? 'inline-block' : 'none';
            console.log('adminButton显示状态:', isAdmin ? '显示' : '隐藏');
        }
        
        if (adminMenuItem) {
            adminMenuItem.style.display = isAdmin ? 'block' : 'none';
            console.log('adminMenuItem显示状态:', isAdmin ? '显示' : '隐藏');
        }
        
        // 查找所有包含"admin"或"管理"的链接和按钮
        const adminElements = document.querySelectorAll('[href*="admin"], [onclick*="admin"], .admin, [class*="admin"]');
        adminElements.forEach(element => {
            // 排除不相关的元素
            if (!element.textContent.includes('管理') && !element.textContent.includes('后台') && !element.href?.includes('/admin/')) {
                return;
            }
            
            element.style.display = isAdmin ? '' : 'none';
        });
        
        // 更新导航栏中的管理员入口
        updateNavigationAdminLinks(isAdmin);
    }
    
    /**
     * 更新导航栏中的管理员链接
     */
    function updateNavigationAdminLinks(isAdmin) {
        // 查找导航栏中的管理员相关链接
        const navLinks = document.querySelectorAll('nav a, .navbar a, .nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href') || '';
            const text = link.textContent || '';
            
            // 检查是否是管理员相关链接
            if (href.includes('/admin/') || text.includes('管理') || text.includes('后台')) {
                link.style.display = isAdmin ? '' : 'none';
                
                // 如果是管理员，确保链接可点击
                if (isAdmin && currentWalletAddress) {
                    // 为管理员链接添加钱包地址参数
                    if (href.includes('/admin/') && !href.includes('wallet_address=')) {
                        const separator = href.includes('?') ? '&' : '?';
                        link.href = href + separator + 'wallet_address=' + encodeURIComponent(currentWalletAddress);
                    }
                }
            }
        });
    }
    
    /**
     * 监听钱包连接状态变化
     */
    function initWalletListener() {
        // 监听钱包管理器的状态变化
        if (window.walletManager) {
            // 如果钱包管理器已经初始化
            const checkCurrentWallet = () => {
                const address = window.walletManager.getConnectedAddress();
                if (address && address !== currentWalletAddress) {
                    checkAdminStatus(address);
                } else if (!address && currentWalletAddress) {
                    // 钱包断开连接
                    currentWalletAddress = null;
                    isAdminUser = false;
                    updateAdminUI(false);
                }
            };
            
            // 立即检查一次
            checkCurrentWallet();
            
            // 定期检查钱包状态
            setInterval(checkCurrentWallet, 2000);
        }
        
        // 监听全局钱包状态变化
        if (window.walletState) {
            const checkGlobalWallet = () => {
                const address = window.walletState.address;
                if (address && address !== currentWalletAddress) {
                    checkAdminStatus(address);
                } else if (!address && currentWalletAddress) {
                    currentWalletAddress = null;
                    isAdminUser = false;
                    updateAdminUI(false);
                }
            };
            
            checkGlobalWallet();
            setInterval(checkGlobalWallet, 2000);
        }
        
        // 监听自定义钱包连接事件
        document.addEventListener('walletConnected', function(event) {
            const address = event.detail?.address;
            if (address) {
                console.log('监听到钱包连接事件:', address);
                checkAdminStatus(address);
            }
        });
        
        document.addEventListener('walletDisconnected', function() {
            console.log('监听到钱包断开事件');
            currentWalletAddress = null;
            isAdminUser = false;
            updateAdminUI(false);
        });
    }
    
    /**
     * 获取当前管理员状态
     */
    function getCurrentAdminStatus() {
        return {
            isAdmin: isAdminUser,
            walletAddress: currentWalletAddress
        };
    }
    
    /**
     * 手动触发管理员检查
     */
    function manualCheckAdmin(walletAddress) {
        return checkAdminStatus(walletAddress);
    }
    
    // 页面加载完成后初始化
    document.addEventListener('DOMContentLoaded', function() {
        console.log('管理员检查脚本初始化');
        
        // 延迟初始化，等待其他脚本加载
        setTimeout(() => {
            initWalletListener();
            
            // 尝试从各种来源获取当前钱包地址
            const possibleAddresses = [
                window.walletState?.address,
                window.walletManager?.getConnectedAddress?.(),
                sessionStorage.getItem('wallet_address'),
                localStorage.getItem('wallet_address'),
                document.cookie.match(/wallet_address=([^;]+)/)?.[1]
            ];
            
            for (const address of possibleAddresses) {
                if (address && address !== 'undefined' && address !== 'null') {
                    console.log('发现已连接的钱包地址:', address);
                    checkAdminStatus(address);
                    break;
                }
            }
        }, 1000);
    });
    
    // 暴露全局函数
    window.adminChecker = {
        checkAdminStatus: manualCheckAdmin,
        getCurrentStatus: getCurrentAdminStatus,
        updateUI: updateAdminUI
    };
    
    console.log('管理员检查脚本加载完成');
})();