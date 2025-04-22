# RWA-HUB API 文档

## API验证规范

### 参数验证规则
所有API请求必须符合以下验证规则:

1. **数据类型验证**
   - `number`: 必须是数字类型
   - `string`: 必须是字符串类型
   - `boolean`: 必须是布尔类型
   - 数组类型必须使用 `Array.isArray()` 验证

2. **必填字段验证**
   - 缺少必填字段将返回400错误
   - 字段类型不匹配将返回400错误

3. **响应格式验证**
   - 所有响应必须包含规定的字段
   - 错误响应必须包含 `error` 和 `code` 字段

### 验证工具使用
前端代码使用 `apiValidator.js` 进行验证:

```javascript
// 1. 创建交易参数验证
const validation = validateCreateTradeParams({
    asset_id: 123,
    amount: "100",
    price: "10.5",
    type: "buy",
    trader_address: "0x..."
});

// 2. 响应格式验证
const responseValidation = validateApiResponse(response, 'CREATE_TRADE');
```

## 基础信息
- 基础URL: `https://rwa-hub.com`
- 所有请求都需要包含 `X-Eth-Address` 头部用于身份验证
- 响应格式: JSON

## 交易相关接口

### 创建交易
- 路径: `/api/trades`
- 方法: `POST`
- 请求头:
  ```
  Content-Type: application/json
  X-Eth-Address: {用户钱包地址}
  ```
- 请求体验证规则:
  ```javascript
  {
    asset_id: {
      type: "number",
      required: true
    },
    amount: {
      type: "string",
      required: true,
      format: "numeric"
    },
    price: {
      type: "string",
      required: true,
      format: "decimal"
    },
    type: {
      type: "string",
      required: true,
      enum: ["buy", "sell"]
    },
    trader_address: {
      type: "string",
      required: true,
      format: "address"
    }
  }
  ```
- 响应验证规则:
  ```javascript
  {
    id: {
      type: "number",
      required: true
    },
    status: {
      type: "string",
      required: true,
      enum: ["pending", "completed", "failed"]
    }
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
    "status": "completed/failed (string)",
    "tx_hash": "交易哈希 (string)",
    "wallet_address": "钱包地址 (string)"
  }
  ```
- 响应:
  ```json
  {
    "success": "更新是否成功 (boolean)"
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