# RWA-HUB API 文档

## 基础信息
- 基础URL: `https://rwa-hub.com`
- 所有请求都需要包含 `X-Eth-Address` 头部用于身份验证
- 响应格式: JSON

## 交易相关接口

### 创建交易
- 路径: `/api/trades/create`
- 方法: `POST`
- 请求头:
  ```
  Content-Type: application/json
  X-Eth-Address: {用户钱包地址}
  ```
- 请求体:
  ```json
  {
    "asset_id": "资产ID",
    "amount": "购买数量",
    "price": "单价",
    "type": "buy/sell"
  }
  ```
- 响应:
  ```json
  {
    "id": "交易ID",
    "asset_id": "资产ID",
    "amount": "数量",
    "price": "价格",
    "status": "pending"
  }
  ```

### 获取交易历史
- 路径: `/api/trades`
- 方法: `GET`
- 参数:
  - asset_id: 资产ID
  - page: 页码
  - per_page: 每页数量
- 响应:
  ```json
  {
    "trades": [
      {
        "id": "交易ID",
        "created_at": "创建时间",
        "type": "buy/sell",
        "amount": "数量",
        "price": "价格",
        "status": "状态",
        "tx_hash": "交易哈希"
      }
    ],
    "pagination": {
      "total": "总记录数",
      "pages": "总页数",
      "current": "当前页"
    }
  }
  ```

### 更新交易状态
- 路径: `/api/trades/{trade_id}/update`
- 方法: `POST`
- 请求头:
  ```
  Content-Type: application/json
  X-Eth-Address: {用户钱包地址}
  ```
- 请求体:
  ```json
  {
    "status": "completed/failed",
    "tx_hash": "交易哈希",
    "wallet_address": "钱包地址"
  }
  ```

## 资产相关接口

### 获取资产详情
- 路径: `/api/assets/{asset_id}`
- 方法: `GET`
- 响应:
  ```json
  {
    "id": "资产ID",
    "name": "资产名称",
    "token_symbol": "代币符号",
    "token_price": "代币价格",
    "token_supply": "代币总量",
    "remaining_supply": "剩余可购买量"
  }
  ```

### 获取资产持有者列表
- 路径: `/api/assets/{asset_id}/holders`
- 方法: `GET`
- 响应:
  ```json
  {
    "holders": [
      {
        "address": "钱包地址",
        "amount": "持有数量",
        "percentage": "持有比例"
      }
    ]
  }
  ```

### 获取资产分红信息
- 路径: `/api/assets/{asset_id}/dividend`
- 方法: `GET`
- 响应:
  ```json
  {
    "total_dividend": "总分红金额",
    "last_dividend": "上次分红金额",
    "next_dividend_date": "下次分红日期"
  }
  ```

## 钱包相关接口

### 获取最新区块哈希
- 路径: `/api/solana/get_latest_blockhash`
- 方法: `GET`
- 响应:
  ```json
  {
    "blockhash": "区块哈希",
    "lastValidBlockHeight": "有效高度"
  }
  ```

### 获取转账参数
- 路径: `/api/solana/get_transfer_params`
- 方法: `GET`
- 参数:
  - from: 发送方地址
  - to: 接收方地址
  - amount: 金额
- 响应:
  ```json
  {
    "from": "发送方地址",
    "to": "接收方地址",
    "amount": "金额",
    "decimals": "小数位数"
  }
  ```

### 发送已签名交易
- 路径: `/api/solana/send_signed_transaction`
- 方法: `POST`
- 请求体:
  ```json
  {
    "signedTransaction": "已签名的交易数据"
  }
  ```
- 响应:
  ```json
  {
    "signature": "交易签名",
    "status": "success/error"
  }
  ```

## 错误处理
所有接口在发生错误时会返回以下格式：
```json
{
  "error": "错误信息",
  "code": "错误代码"
}
```

常见错误代码：
- 400: 请求参数错误
- 401: 未授权
- 403: 权限不足
- 404: 资源不存在
- 500: 服务器内部错误

## 注意事项
1. 所有金额相关的数值都使用字符串类型
2. 时间格式使用ISO 8601标准
3. 交易状态包括：pending(处理中)、completed(已完成)、failed(失败)
4. 所有涉及钱包地址的字段都应该使用checksum格式 