#!/bin/bash
# 管理员表修复工具
# 用法: ./fix_admin.sh [参数]

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 显示帮助
function show_help {
  echo -e "${BLUE}管理员表修复工具${NC}"
  echo "用法: ./fix_admin.sh [命令] [参数]"
  echo ""
  echo "命令:"
  echo "  check             检查管理员表结构和数据"
  echo "  fix               修复管理员表结构"
  echo "  add               添加管理员用户"
  echo "  help              显示此帮助信息"
  echo ""
  echo "选项:"
  echo "  --wallet-address  管理员钱包地址"
  echo "  --username        管理员用户名"
  echo "  --role            管理员角色 (admin或super_admin)"
  echo ""
  echo "示例:"
  echo "  ./fix_admin.sh check"
  echo "  ./fix_admin.sh fix"
  echo "  ./fix_admin.sh add --wallet-address HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd --username 测试管理员 --role super_admin"
}

# 检查是否在正确的目录中
if [ ! -f "app.py" ] || [ ! -d "app" ]; then
  echo -e "${RED}错误: 请在项目根目录中运行此脚本${NC}"
  exit 1
fi

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
  echo -e "${RED}错误: 找不到python3命令${NC}"
  exit 1
fi

# 如果没有参数，显示帮助
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

# 解析命令
COMMAND=$1
shift

case $COMMAND in
  check)
    echo -e "${BLUE}检查管理员表结构和数据...${NC}"
    python3 check_admin_table.py
    ;;
    
  fix)
    echo -e "${BLUE}修复管理员表结构...${NC}"
    python3 check_admin_table.py --fix
    ;;
    
  add)
    # 解析添加管理员的参数
    WALLET_ADDRESS=""
    USERNAME=""
    ROLE="admin"
    
    while (( "$#" )); do
      case "$1" in
        --wallet-address)
          WALLET_ADDRESS=$2
          shift 2
          ;;
        --username)
          USERNAME=$2
          shift 2
          ;;
        --role)
          ROLE=$2
          shift 2
          ;;
        *)
          echo -e "${RED}错误: 未知参数 $1${NC}"
          show_help
          exit 1
          ;;
      esac
    done
    
    # 检查必要参数
    if [ -z "$WALLET_ADDRESS" ] || [ -z "$USERNAME" ]; then
      echo -e "${RED}错误: 添加管理员需要 --wallet-address 和 --username 参数${NC}"
      show_help
      exit 1
    fi
    
    echo -e "${BLUE}添加管理员用户...${NC}"
    echo -e "钱包地址: ${YELLOW}$WALLET_ADDRESS${NC}"
    echo -e "用户名: ${YELLOW}$USERNAME${NC}"
    echo -e "角色: ${YELLOW}$ROLE${NC}"
    
    # 使用setup_admin_user.py脚本添加管理员
    python3 setup_admin_user.py --wallet-address "$WALLET_ADDRESS" --username "$USERNAME" --role "$ROLE" --force
    ;;
    
  help)
    show_help
    ;;
    
  *)
    echo -e "${RED}错误: 未知命令 $COMMAND${NC}"
    show_help
    exit 1
    ;;
esac

echo -e "${GREEN}完成!${NC}" 