#!/bin/bash
# AI Node 3-Group Test Script for node-22
# 第一组：OpenAI (chatgpt.com, openai.com)
# 第二组：Gemini (gemini.google.com) - 真实可用性测试
# 第三组：Google 搜索 (google.com, gstatic.com)

API="http://127.0.0.1:19090"
RESULTS="/tmp/ai-node-3group-results.txt"

# 清空结果文件
> $RESULTS

# 需要测试的节点（按优先级：SS -> VLESS -> HY2）
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

echo "=== AI Node 3-Group Test Results ===" >> $RESULTS
echo "Test Time: $(date)" >> $RESULTS
echo "" >> $RESULTS

# 第一组：OpenAI 测试
echo "=== GROUP 1: OpenAI ===" >> $RESULTS
echo "Testing: chatgpt.com, openai.com, oaistatic.com" >> $RESULTS
echo "" >> $RESULTS

for NODE in "${NODES[@]}"; do
    # 切换到该节点
    curl -s -X PUT "$API/proxies/AI-Test" -d "{\"name\":\"$NODE\"}" > /dev/null
    sleep 0.5

    NODE_TYPE=$(curl -s "$API/proxies/$NODE" | jq -r '.type // "Unknown"')

    # 测试 ChatGPT
    CHATGPT="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://chatgpt.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "403" ]]; then
        CHATGPT="✅"
    fi

    # 测试 OpenAI
    OPENAI="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://openai.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        OPENAI="✅"
    fi

    # 稳定性 (3 次)
    SUCCESS=0
    for i in {1..3}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 8 \
            --proxy "http://127.0.0.1:7895" "https://chatgpt.com" 2>/dev/null)
        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "403" ]]; then
            ((SUCCESS++))
        fi
        sleep 0.3
    done

    if [[ $SUCCESS -eq 3 ]]; then
        STABILITY="高 (3/3)"
    elif [[ $SUCCESS -ge 2 ]]; then
        STABILITY="中 ($SUCCESS/3)"
    else
        STABILITY="低 ($SUCCESS/3)"
    fi

    echo "OpenAI | $NODE ($NODE_TYPE): CG=$CHATGPT OI=$OPENAI ST=$STABILITY" >> $RESULTS
done

echo "" >> $RESULTS

# 第二组：Gemini 真实可用性测试
echo "=== GROUP 2: Gemini (Real Request Test) ===" >> $RESULTS
echo "Testing: gemini.google.com - Real request test" >> $RESULTS
echo "" >> $RESULTS

for NODE in "${NODES[@]}"; do
    curl -s -X PUT "$API/proxies/AI-Test" -d "{\"name\":\"$NODE\"}" > /dev/null
    sleep 0.5

    NODE_TYPE=$(curl -s "$API/proxies/$NODE" | jq -r '.type // "Unknown"')

    GEMINI_HOME="❌"
    GEMINI_REAL="❌"
    FIRST_BYTE="N/A"

    # 测试首页
    START=$(date +%s%3N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://gemini.google.com" 2>/dev/null)
    END=$(date +%s%3N)
    LATENCY=$((END - START))

    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "404" ]]; then
        GEMINI_HOME="✅"
        FIRST_BYTE="${LATENCY}ms"
    fi

    # 真实请求测试：尝试访问 Gemini API 端点
    # 使用一个不会真正执行的请求来测试连通性
    API_RESPONSE=$(curl -s --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" \
        "https://generativelanguage.googleapis.com/v1/models" 2>/dev/null)

    # 检查是否得到有效响应（不是 DNS 错误或连接失败）
    if [[ -n "$API_RESPONSE" ]] || [[ "$API_RESPONSE" != "" ]]; then
        # 检查是否包含错误信息但不是连接错误
        if echo "$API_RESPONSE" | grep -qE "error|Error|ERROR|permission|key|auth|403|401|404" 2>/dev/null; then
            # 有响应，说明连接成功，只是认证失败 - 这是"好"的错误
            GEMINI_REAL="✅ (API reachable)"
        elif echo "$API_RESPONSE" | grep -qE "models|Model|content" 2>/dev/null; then
            GEMINI_REAL="✅ (API working)"
        else
            # 有其他响应，也算通
            GEMINI_REAL="⚠️ (response received)"
        fi
    fi

    # 稳定性 (3 次)
    SUCCESS=0
    for i in {1..3}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 8 \
            --proxy "http://127.0.0.1:7895" "https://gemini.google.com" 2>/dev/null)
        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "404" ]]; then
            ((SUCCESS++))
        fi
        sleep 0.3
    done

    if [[ $SUCCESS -eq 3 ]]; then
        STABILITY="高 (3/3)"
    elif [[ $SUCCESS -ge 2 ]]; then
        STABILITY="中 ($SUCCESS/3)"
    else
        STABILITY="低 ($SUCCESS/3)"
    fi

    echo "Gemini | $NODE ($NODE_TYPE): HOME=$GEMINI_HOME API=$GEMINI_REAL FB=$FIRST_BYTE ST=$STABILITY" >> $RESULTS
done

echo "" >> $RESULTS

# 第三组：Google 搜索
echo "=== GROUP 3: Google Search ===" >> $RESULTS
echo "Testing: google.com, www.google.com, gstatic.com" >> $RESULTS
echo "" >> $RESULTS

for NODE in "${NODES[@]}"; do
    curl -s -X PUT "$API/proxies/AI-Test" -d "{\"name\":\"$NODE\"}" > /dev/null
    sleep 0.5

    NODE_TYPE=$(curl -s "$API/proxies/$NODE" | jq -r '.type // "Unknown"')

    GOOGLE="❌"
    WWW_GOOGLE="❌"
    GSTATIC="❌"
    FIRST_BYTE="N/A"

    # 测试 google.com
    START=$(date +%s%3N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://google.com" 2>/dev/null)
    END=$(date +%s%3N)
    LATENCY=$((END - START))
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        GOOGLE="✅"
        FIRST_BYTE="${LATENCY}ms"
    fi

    # 测试 www.google.com
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.google.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        WWW_GOOGLE="✅"
    fi

    # 测试 gstatic.com
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.gstatic.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        GSTATIC="✅"
    fi

    # 稳定性 (3 次)
    SUCCESS=0
    for i in {1..3}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 8 \
            --proxy "http://127.0.0.1:7895" "https://www.google.com" 2>/dev/null)
        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
            ((SUCCESS++))
        fi
        sleep 0.3
    done

    if [[ $SUCCESS -eq 3 ]]; then
        STABILITY="高 (3/3)"
    elif [[ $SUCCESS -ge 2 ]]; then
        STABILITY="中 ($SUCCESS/3)"
    else
        STABILITY="低 ($SUCCESS/3)"
    fi

    echo "Google | $NODE ($NODE_TYPE): G=$GOOGLE WG=$WWW_GOOGLE GS=$GSTATIC FB=$FIRST_BYTE ST=$STABILITY" >> $RESULTS
done

echo "" >> $RESULTS
echo "=== Test Complete ===" >> $RESULTS

cat $RESULTS
