#!/bin/bash
# AI Node Test Script for node-22
# 测试节点对 AI 网站的实际可用性

API="http://127.0.0.1:19090"
RESULTS="/tmp/ai-node-results.txt"

# 清空结果文件
> $RESULTS

# 测试站点列表
SITES=(
    "chatgpt.com"
    "openai.com"
    "gemini.google.com"
    "google.com"
    "www.google.com"
)

# 需要测试的节点（按优先级：SS -> VLESS -> HY2，跳过 TUIC）
NODES=(
    "ss-US-1"
    "US-1"
    "US-2"
    "US-3-gemini"
    "JP-1"
    "JP-2"
    "JP-3"
    "JP-4"
    "SG-1"
    "SG-2"
    "SG-3"
    "HK-1"
    "HK-2"
    "HK-3"
    "HK-4"
    "KR-1"
    "KR-2"
    "US-gemini-1"
    "US1-HY2"
    "US2-HY2"
    "US3-HY2"
    "US4-HY2"
    "US5-HY2"
    "US6-HY2"
    "US7-HY2"
    "US8-HY2"
    "JP6-HY2"
    "JP7-HY2"
    "JP8-HY2"
    "HK2-HY2"
    "HK3-HY2"
    "HK4-HY2"
    "HK5-HY2"
    "SG1-HY2"
    "SG2-HY2"
)

echo "=== AI Node Test Results ===" >> $RESULTS
echo "Test Time: $(date)" >> $RESULTS
echo "" >> $RESULTS

for NODE in "${NODES[@]}"; do
    echo "Testing $NODE..."

    # 切换到该节点
    curl -s -X PUT "$API/proxies/AI-Test" -d "{\"name\":\"$NODE\"}" > /dev/null
    sleep 1

    # 记录节点类型
    NODE_TYPE=$(curl -s "$API/proxies/$NODE" | jq -r '.type // "Unknown"')

    # 测试结果
    CHATGPT="❌"
    OPENAI="❌"
    GEMINI="❌"
    GOOGLE="❌"
    FIRST_BYTE="N/A"
    STABILITY="N/A"

    # 测试 Google（最简单）
    START=$(date +%s%3N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.google.com" 2>/dev/null)
    END=$(date +%s%3N)
    LATENCY=$((END - START))

    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        GOOGLE="✅"
        FIRST_BYTE="${LATENCY}ms"
    fi

    # 测试 ChatGPT
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://chatgpt.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "403" ]]; then
        CHATGPT="✅"
    fi

    # 测试 OpenAI
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://openai.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        OPENAI="✅"
    fi

    # 测试 Gemini
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://gemini.google.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "404" ]]; then
        GEMINI="✅"
    fi

    # 稳定性测试（5 次 Google 请求）
    SUCCESS=0
    for i in {1..5}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 8 \
            --proxy "http://127.0.0.1:7895" "https://www.google.com" 2>/dev/null)
        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
            ((SUCCESS++))
        fi
        sleep 0.5
    done

    if [[ $SUCCESS -eq 5 ]]; then
        STABILITY="高 (5/5)"
    elif [[ $SUCCESS -ge 3 ]]; then
        STABILITY="中 ($SUCCESS/5)"
    else
        STABILITY="低 ($SUCCESS/5)"
    fi

    # 记录结果
    echo "$NODE ($NODE_TYPE): CG=$CHATGPT OI=$OPENAI GM=$GEMINI GG=$GOOGLE FB=$FIRST_BYTE ST=$STABILITY" >> $RESULTS
done

echo "" >> $RESULTS
echo "=== Test Complete ===" >> $RESULTS

cat $RESULTS
