class AuthService {
    constructor() {
        this.web3 = null;
        this.account = null;
        this.token = localStorage.getItem("auth_token");
        this.initWeb3();
    }

    async initWeb3() {
        if (typeof window.ethereum !== "undefined") {
            this.web3 = new Web3(window.ethereum);
            // 监听账户变化
            window.ethereum.on("accountsChanged", (accounts) => {
                if (accounts.length === 0) {
                    this.logout();
                } else {
                    this.account = accounts[0];
                    this.emit("accountChanged", this.account);
                }
            });
            return true;
        } else {
            console.error("Please install MetaMask!");
            return false;
        }
    }

    async connect() {
        try {
            // 请求用户授权
            const accounts = await window.ethereum.request({ 
                method: "eth_requestAccounts" 
            });
            this.account = accounts[0];
            
            // 获取nonce
            const nonceResponse = await fetch(`${window.appConfig.API_BASE_URL}/api/auth/nonce`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ address: this.account })
            });
            const nonceData = await nonceResponse.json();
            
            // 签名消息
            const signature = await this.web3.eth.personal.sign(
                nonceData.nonce,
                this.account,
                "" // MetaMask会忽略密码参数
            );
            
            // 验证签名并获取令牌
            const authResponse = await fetch(`${window.appConfig.API_BASE_URL}/api/auth/verify`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    address: this.account,
                    signature: signature
                })
            });
            
            const authData = await authResponse.json();
            if (authResponse.ok) {
                this.token = authData.token;
                localStorage.setItem("auth_token", this.token);
                this.emit("login", this.account);
                return true;
            } else {
                throw new Error(authData.error);
            }
            
        } catch (error) {
            console.error("Connection failed:", error);
            throw error;
        }
    }

    logout() {
        this.token = null;
        this.account = null;
        localStorage.removeItem("auth_token");
        this.emit("logout");
    }

    isAuthenticated() {
        return !!this.token && !!this.account;
    }

    getAuthHeaders() {
        return this.token ? {
            "Authorization": `Bearer ${this.token}`
        } : {};
    }

    // 简单的事件系统
    listeners = {};
    
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }
    
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => callback(data));
        }
    }
}

// 创建全局实例
window.authService = new AuthService();