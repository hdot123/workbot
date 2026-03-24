#!/bin/bash
# AI Node Video & X Group Test Script for node-22
# 视频组：youtube.com, googlevideo.com, ytimg.com
# X 组：x.com, twitter.com, twimg.com

API="http://127.0.0.1:19090"
RESULTS="/tmp/ai-node-video-x-results.txt"

# 待测节点（未通过 AI/Google 组的节点）
NODES=(
    # 香港 VLESS
    "HK-1"
    "HK-2"
    "HK-3"
    "HK-4"
    # 香港 HY2
    "HK2-HY2"
    "HK3-HY2"
    "HK4-HY2"
    "HK5-HY2"
    # 韩国 VLESS
    "KR-1"
    "KR-2"
    # 美国 VLESS
    "US-1"
    "US-2"
    "US-3"
    # 美国 HY2
    "US-gemini-1"
    "US1-HY2"
    "US2-HY2"
    "US3-HY2"
    "US4-HY2"
    "US5-HY2"
    "US6-HY2"
    "US7-HY2"
    "US8-HY2"
)

# 清空结果文件
> $RESULTS

echo "=== Video & X Group Test Results ===" >> $RESULTS
echo "Test Time: $(date)" >> $RESULTS
echo "" >> $RESULTS

# ============================================
# 视频组测试
# ============================================
echo "=== GROUP: Video (YouTube) ===" >> $RESULTS
echo "Testing: youtube.com, youtu.be, googlevideo.com, ytimg.com" >> $RESULTS
echo "" >> $RESULTS

for NODE in "${NODES[@]}"; do
    # 切换到该节点
    curl -s -X PUT "$API/proxies/Video-Test" -d "{\"name\":\"$NODE\"}" > /dev/null
    sleep 0.5

    NODE_TYPE=$(curl -s "$API/proxies/$NODE" | jq -r '.type // "Unknown"')

    # 测试 youtube.com
    YT="❌"
    START=$(date +%s%3N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.youtube.com" 2>/dev/null)
    END=$(date +%s%3N)
    LATENCY=$((END - START))
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        YT="✅"
        FIRST_BYTE="${LATENCY}ms"
    fi

    # 测试 youtu.be
    YTB="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://youtu.be" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        YTB="✅"
    fi

    # 测试 googlevideo.com (视频资源)
    GV="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.googlevideo.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        GV="✅"
    fi

    # 测试 ytimg.com (缩略图)
    YTI="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.ytimg.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        YTI="✅"
    fi

    # 稳定性 (3 次)
    SUCCESS=0
    for i in {1..3}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 8 \
            --proxy "http://127.0.0.1:7895" "https://www.youtube.com" 2>/dev/null)
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

    echo "Video | $NODE ($NODE_TYPE): YT=$YT YTB=$YTB GV=$GV YTI=$YTI FB=$FIRST_BYTE ST=$STABILITY" >> $RESULTS
done

echo "" >> $RESULTS

# ============================================
# X 组测试
# ============================================
echo "=== GROUP: X (Twitter) ===" >> $RESULTS
echo "Testing: x.com, twitter.com, t.co, twimg.com" >> $RESULTS
echo "" >> $RESULTS

for NODE in "${NODES[@]}"; do
    # 切换到该节点
    curl -s -X PUT "$API/proxies/X-Test" -d "{\"name\":\"$NODE\"}" > /dev/null
    sleep 0.5

    NODE_TYPE=$(curl -s "$API/proxies/$NODE" | jq -r '.type // "Unknown"')

    # 测试 x.com
    XCOM="❌"
    START=$(date +%s%3N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://x.com" 2>/dev/null)
    END=$(date +%s%3N)
    LATENCY=$((END - START))
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        XCOM="✅"
        FIRST_BYTE="${LATENCY}ms"
    fi

    # 测试 twitter.com
    TWI="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://twitter.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        TWI="✅"
    fi

    # 测试 t.co (短链接)
    TCO="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://t.co" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        TCO="✅"
    fi

    # 测试 twimg.com (图片资源)
    TWIG="❌"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 -m 10 \
        --proxy "http://127.0.0.1:7895" "https://www.twimg.com" 2>/dev/null)
    if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" ]]; then
        TWIG="✅"
    fi

    # 稳定性 (3 次)
    SUCCESS=0
    for i in {1..3}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 -m 8 \
            --proxy "http://127.0.0.1:7895" "https://x.com" 2>/dev/null)
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

    echo "X | $NODE ($NODE_TYPE): XC=$XCOM TW=$TWI TC=$TCO TI=$TWIG FB=$FIRST_BYTE ST=$STABILITY" >> $RESULTS
done

echo "" >> $RESULTS
echo "=== Test Complete ===" >> $RESULTS

cat $RESULTS
