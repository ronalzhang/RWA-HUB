#!/bin/bash
# 设置CRYPTO_PASSWORD环境变量

echo "🔐 设置CRYPTO_PASSWORD环境变量..."

# 设置当前会话的环境变量
export CRYPTO_PASSWORD='123abc74531'

# 添加到.bashrc（如果存在）
if [ -f ~/.bashrc ]; then
    if ! grep -q "CRYPTO_PASSWORD" ~/.bashrc; then
        echo "export CRYPTO_PASSWORD='123abc74531'" >> ~/.bashrc
        echo "✅ 已添加到 ~/.bashrc"
    else
        echo "⚠️  ~/.bashrc 中已存在 CRYPTO_PASSWORD"
    fi
fi

# 添加到.profile（如果存在）
if [ -f ~/.profile ]; then
    if ! grep -q "CRYPTO_PASSWORD" ~/.profile; then
        echo "export CRYPTO_PASSWORD='123abc74531'" >> ~/.profile
        echo "✅ 已添加到 ~/.profile"
    else
        echo "⚠️  ~/.profile 中已存在 CRYPTO_PASSWORD"
    fi
fi

echo "✅ 环境变量设置完成"
echo "💡 请运行: source ~/.bashrc 或重新登录以生效"
