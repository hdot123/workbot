# ClawRouter v2.7.0 部署与验收手册

**目标服务器**: 192.168.88.27:3000
**当前版本**: v2.6.0
**目标版本**: v2.7.0
**功能**: 阿里云 Embedding 支持（aliyun-embedding）

---

## 一、部署前检查项

### 1.1 本地代码检查

```bash
# 检查本地代码版本
head -15 /Users/busiji/passkills/tmp/clawrouter-deploy/src/server.js | grep "v2.7.0"

# 检查 AliyunEmbeddingProvider 类存在
grep -c "class AliyunEmbeddingProvider" /Users/busiji/passkills/tmp/clawrouter-deploy/src/server.js
# 预期输出：1

# 检查 protocol-adapter.js 支持 aliyun brand
grep "aliyun" /Users/busiji/passkills/tmp/clawrouter-deploy/src/protocol-adapter.js
# 预期输出：包含 aliyun 相关配置
```

### 1.2 远程服务状态确认

```bash
# 检查远程服务当前版本
curl -s http://192.168.88.27:3000/health | jq '.version'
# 预期输出："2.6.0"

# 检查服务是否正常
curl -s http://192.168.88.27:3000/health | jq '.ok'
# 预期输出：true

# 确认端口可访问
nc -zv 192.168.88.27 3000
```

### 1.3 环境变量准备

**必需环境变量**：
```bash
DASHSCOPE_API_KEY=sk-xxxxxxxx  # 阿里云 API Key
```

**可选环境变量**：
```bash
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSION=1024
```

---

## 二、备份当前版本

### 2.1 SSH 登录远程服务器

```bash
ssh user@192.168.88.27
# 替换 user 为实际用户名
```

### 2.2 查找部署目录

```bash
# 方法 1: 查找监听 3000 端口的进程
lsof -i :3000 | grep LISTEN

# 方法 2: 查找 Docker 容器
docker ps | grep 3000

# 方法 3: 查找 PM2 进程
pm2 list | grep clawrouter

# 常见部署目录：
# - /opt/clawrouter
# - /home/user/clawrouter
# - /var/www/clawrouter
```

### 2.3 执行备份

假设部署目录为 `/opt/clawrouter`：

```bash
cd /opt/clawrouter

# 备份当前版本
sudo cp src/server.js src/server.js.v2.6.0.bak
sudo cp src/protocol-adapter.js src/protocol-adapter.js.v2.6.0.bak

# 备份环境变量文件（如果有）
sudo cp .env .env.v2.6.0.bak

# 创建备份目录（推荐）
sudo mkdir -p backups/v2.6.0
sudo cp src/*.js backups/v2.6.0/
sudo cp .env backups/v2.6.0/ 2>/dev/null || true

# 验证备份
ls -lh backups/v2.6.0/
```

---

## 三、上传新版本代码

### 3.1 使用 scp 上传

```bash
# 在本地执行
# 上传 server.js
scp /Users/busiji/passkills/tmp/clawrouter-deploy/src/server.js \
    user@192.168.88.27:/opt/clawrouter/src/

# 上传 protocol-adapter.js
scp /Users/busiji/passkills/tmp/clawrouter-deploy/src/protocol-adapter.js \
    user@192.168.88.27:/opt/clawrouter/src/

# 如果有环境变量文件更新
scp /Users/busiji/passkills/tmp/clawrouter-deploy/config/.env \
    user@192.168.88.27:/opt/clawrouter/
```

### 3.2 使用 rsync 上传（推荐）

```bash
# 在本地执行
# 同步整个 src 目录
rsync -avz --progress \
    /Users/busiji/passkills/tmp/clawrouter-deploy/src/ \
    user@192.168.88.27:/opt/clawrouter/src/

# 只同步修改的文件
rsync -avz --progress \
    /Users/busiji/passkills/tmp/clawrouter-deploy/src/server.js \
    user@192.168.88.27:/opt/clawrouter/src/

rsync -avz --progress \
    /Users/busiji/passkills/tmp/clawrouter-deploy/src/protocol-adapter.js \
    user@192.168.88.27:/opt/clawrouter/src/
```

### 3.3 验证上传成功

```bash
# SSH 登录远程服务器
ssh user@192.168.88.27

# 检查文件时间戳
ls -lh /opt/clawrouter/src/*.js

# 检查文件版本
head -15 /opt/clawrouter/src/server.js | grep "v2.7.0"

# 检查文件完整性
wc -l /opt/clawrouter/src/server.js
# 预期：1000+ 行
```

---

## 四、环境变量配置

### 4.1 检查现有环境变量

```bash
# SSH 登录远程服务器
cd /opt/clawrouter

# 如果使用 .env 文件
cat .env | grep DASHSCOPE

# 如果使用 systemd
systemctl show clawrouter | grep Environment

# 如果使用 Docker Compose
docker compose config | grep DASHSCOPE
```

### 4.2 添加/更新环境变量

#### Docker Compose 方式

编辑 `docker-compose.yml`：

```yaml
services:
  clawrouter:
    environment:
      - DASHSCOPE_API_KEY=sk-xxxxxxxx
      - DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
      - DASHSCOPE_EMBEDDING_DIMENSION=1024
```

或使用 `.env` 文件：

```bash
cat >> .env <<EOF
# 阿里云 Embedding 配置
DASHSCOPE_API_KEY=sk-xxxxxxxx
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_EMBEDDING_DIMENSION=1024
EOF

chmod 600 .env
```

#### PM2 方式

```bash
# 创建/编辑 ecosystem.config.js
cat > ecosystem.config.js <<EOF
module.exports = {
  apps: [{
    name: 'clawrouter',
    script: 'src/server.js',
    env: {
      DASHSCOPE_API_KEY: 'sk-xxxxxxxx',
      DASHSCOPE_EMBEDDING_MODEL: 'text-embedding-v4',
      DASHSCOPE_EMBEDDING_DIMENSION: 1024
    }
  }]
}
EOF
```

#### systemd 方式

```bash
sudo systemctl edit clawrouter

# 添加：
[Service]
Environment="DASHSCOPE_API_KEY=sk-xxxxxxxx"
Environment="DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4"
Environment="DASHSCOPE_EMBEDDING_DIMENSION=1024"

# 保存并重新加载
sudo systemctl daemon-reload
```

### 4.3 验证环境变量

```bash
# 重启服务后，检查环境变量是否生效
curl -s http://192.168.88.27:3000/health | jq '.embeddings.aliyun.api_key_configured'
# 预期输出：true
```

---

## 五、重启服务

### 5.1 Docker Compose 场景

```bash
# SSH 登录远程服务器
cd /opt/clawrouter

# 方式 1: 重启容器（推荐）
docker compose restart

# 方式 2: 重新构建并启动
docker compose up -d --build

# 方式 3: 停止 + 启动
docker compose down
docker compose up -d

# 查看日志
docker compose logs -f --tail=100

# 查看容器状态
docker compose ps
```

### 5.2 PM2 场景

```bash
# SSH 登录远程服务器
cd /opt/clawrouter

# 方式 1: 重启（推荐）
pm2 restart clawrouter

# 方式 2: 重载（零停机）
pm2 reload clawrouter

# 方式 3: 停止 + 启动
pm2 stop clawrouter
pm2 start clawrouter

# 查看日志
pm2 logs clawrouter --lines 100

# 查看状态
pm2 status
```

### 5.3 systemd 场景

```bash
# SSH 登录远程服务器

# 方式 1: 重启（推荐）
sudo systemctl restart clawrouter

# 方式 2: 重载配置
sudo systemctl reload clawrouter

# 查看日志
sudo journalctl -u clawrouter -f

# 查看状态
sudo systemctl status clawrouter
```

### 5.4 手动进程场景

```bash
# SSH 登录远程服务器

# 查找进程 PID
ps aux | grep "node.*server.js" | grep -v grep

# 优雅停止（使用 SIGTERM）
kill -15 <PID>

# 强制停止（如果无响应）
kill -9 <PID>

# 启动新进程
cd /opt/clawrouter
nohup node src/server.js > logs/clawrouter.log 2>&1 &

# 查看日志
tail -f logs/clawrouter.log
```

---

## 六、验证版本升级

### 6.1 检查版本号

```bash
curl -s http://192.168.88.27:3000/health | jq '.version'
# 预期输出："2.7.0"
```

### 6.2 检查 features

```bash
curl -s http://192.168.88.27:3000/health | jq '.features' | grep -E "(aliyun|batch|realtime)"
# 预期输出包含：
# - "aliyun-embedding"
# - "batch-documents"
# - "realtime-query"
```

### 6.3 检查 embeddings 配置

```bash
curl -s http://192.168.88.27:3000/health | jq '.embeddings'
# 预期输出：
# {
#   "voyage": {...},
#   "aliyun": {
#     "external_model": "aliyun-embedding",
#     "internal_model": "text-embedding-v4",
#     "dimension": 1024,
#     "api_key_configured": true,
#     "strategy": {
#       "single_valid_text": "realtime sync (在线检索)",
#       "multiple_valid_texts": "async batch (文档入库)"
#     }
#   }
# }
```

### 6.4 完整健康检查

```bash
curl -s http://192.168.88.27:3000/health | jq '{
  version,
  ok,
  features_count: (.features | length),
  embeddings_providers: (.embeddings | keys),
  aliyun_configured: .embeddings.aliyun.api_key_configured
}'
# 预期输出：
# {
#   "version": "2.7.0",
#   "ok": true,
#   "features_count": 9,
#   "embeddings_providers": ["voyage", "aliyun"],
#   "aliyun_configured": true
# }
```

---

## 七、完整验收测试

### 7.1 测试 /v1/models

```bash
# 检查 aliyun-embedding 是否暴露
curl -s http://192.168.88.27:3000/v1/models | \
  jq '.data[] | select(.id == "aliyun-embedding")'

# 预期输出：
# {
#   "object": "model",
#   "id": "aliyun-embedding",
#   "brand": "aliyun",
#   "owned_by": "clawrouter-gateway",
#   "supported_protocols": ["openai"],
#   "capabilities": ["embeddings"],
#   "description": "阿里云 embedding：文档入库自动 batch，在线检索实时调用"
# }

# 确认不暴露 text-embedding-v4
curl -s http://192.168.88.27:3000/v1/models | \
  jq '.data[] | select(.id | contains("text-embedding"))'
# 预期输出：无
```

### 7.2 测试单条字符串 → realtime sync

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": "这是一条查询文本"}' \
  | jq '{model, data_count: (.data | length), embedding_dim: (.data[0].embedding | length), usage}'

# 预期输出：
# {
#   "model": "aliyun-embedding",
#   "data_count": 1,
#   "embedding_dim": 1024,
#   "usage": {"prompt_tokens": 10, "total_tokens": 10}
# }
```

### 7.3 测试单条数组 → realtime sync

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": ["这是一条查询文本"]}' \
  | jq '{model, data_count: (.data | length)}'

# 预期输出：
# {"model": "aliyun-embedding", "data_count": 1}
```

### 7.4 测试多条数组 → async batch

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": ["文档内容1", "文档内容2", "文档内容3"]}' \
  | jq '{model, data_count: (.data | length), indices: [.data[].index]}'

# 预期输出：
# {
#   "model": "aliyun-embedding",
#   "data_count": 3,
#   "indices": [0, 1, 2]
# }
```

### 7.5 测试空数组 → 400

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": []}'

# 预期输出：
# {"error": "input 为空，请提供字符串或字符串数组"}
```

### 7.6 测试空字符串 → 400

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": ""}'

# 预期输出：
# {"error": "input 为空，请提供字符串或字符串数组"}
```

### 7.7 测试全空白 → 400

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": ["  ", "", "   "]}'

# 预期输出：
# {"error": "没有可用于 embedding 的有效文本（全部为空或空白）"}
```

### 7.8 测试混合有效和空白 → realtime sync

```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": ["有效文本", "   ", ""]}' \
  | jq '{model, data_count: (.data | length)}'

# 预期输出：
# {"model": "aliyun-embedding", "data_count": 1}
```

### 7.9 测试与 Voyage 共存

```bash
# 测试 Voyage 仍正常工作
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "voyage", "input": "测试文本"}' \
  | jq '{model, data_count: (.data | length)}'

# 预期输出：
# {"model": "voyage", "data_count": 1}
```

### 7.10 一键完整验收脚本

```bash
cat > /tmp/clawrouter-v2.7.0-test.sh <<'EOF'
#!/bin/bash
set -e

BASE_URL="http://192.168.88.27:3000"
PASS=0
FAIL=0

echo "=== ClawRouter v2.7.0 验收测试 ==="
echo ""

# 测试 1: 版本号
echo -n "1. 版本号检查... "
VERSION=$(curl -s $BASE_URL/health | jq -r '.version')
if [ "$VERSION" == "2.7.0" ]; then
    echo "✅ PASS ($VERSION)"
    ((PASS++))
else
    echo "❌ FAIL (expected 2.7.0, got $VERSION)"
    ((FAIL++))
fi

# 测试 2: aliyun-embedding 模型暴露
echo -n "2. aliyun-embedding 模型暴露... "
COUNT=$(curl -s $BASE_URL/v1/models | jq '[.data[] | select(.id == "aliyun-embedding")] | length')
if [ "$COUNT" == "1" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (count: $COUNT)"
    ((FAIL++))
fi

# 测试 3: text-embedding-v4 不暴露
echo -n "3. text-embedding-v4 不暴露... "
COUNT=$(curl -s $BASE_URL/v1/models | jq '[.data[] | select(.id | contains("text-embedding"))] | length')
if [ "$COUNT" == "0" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (exposed: $COUNT)"
    ((FAIL++))
fi

# 测试 4: 单条字符串
echo -n "4. 单条字符串 embedding... "
RESULT=$(curl -s $BASE_URL/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model": "aliyun-embedding", "input": "测试"}' \
    | jq '{model, count: (.data | length), dim: (.data[0].embedding | length)}')
MODEL=$(echo $RESULT | jq -r '.model')
COUNT=$(echo $RESULT | jq -r '.count')
DIM=$(echo $RESULT | jq -r '.dim')
if [ "$MODEL" == "aliyun-embedding" ] && [ "$COUNT" == "1" ] && [ "$DIM" == "1024" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL ($RESULT)"
    ((FAIL++))
fi

# 测试 5: 多条数组
echo -n "5. 多条数组 embedding... "
INDICES=$(curl -s $BASE_URL/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model": "aliyun-embedding", "input": ["文档1", "文档2"]}' \
    | jq -r '.data | map(.index) | join(",")')
if [ "$INDICES" == "0,1" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (indices: $INDICES)"
    ((FAIL++))
fi

# 测试 6: 空数组 400
echo -n "6. 空数组返回 400... "
ERROR=$(curl -s $BASE_URL/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model": "aliyun-embedding", "input": []}' \
    | jq -r '.error // empty')
if [[ "$ERROR" == *"input 为空"* ]]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (error: $ERROR)"
    ((FAIL++))
fi

# 测试 7: 全空白 400
echo -n "7. 全空白返回 400... "
ERROR=$(curl -s $BASE_URL/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model": "aliyun-embedding", "input": ["  ", ""]}' \
    | jq -r '.error // empty')
if [[ "$ERROR" == *"没有可用的有效文本"* ]]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (error: $ERROR)"
    ((FAIL++))
fi

# 测试 8: Voyage 共存
echo -n "8. Voyage 共存测试... "
MODEL=$(curl -s $BASE_URL/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{"model": "voyage", "input": "测试"}' \
    | jq -r '.model')
if [ "$MODEL" == "voyage" ]; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL (model: $MODEL)"
    ((FAIL++))
fi

echo ""
echo "================================"
echo "测试结果: ✅ $PASS 通过, ❌ $FAIL 失败"
echo "================================"

if [ $FAIL -eq 0 ]; then
    echo "🎉 所有测试通过！v2.7.0 部署成功！"
    exit 0
else
    echo "⚠️  部分测试失败，请检查日志"
    exit 1
fi
EOF

chmod +x /tmp/clawrouter-v2.7.0-test.sh
bash /tmp/clawrouter-v2.7.0-test.sh
```

---

## 八、日志检查

### 8.1 Docker Compose 日志

```bash
# 查看最近 100 行日志
docker compose logs --tail=100

# 实时跟踪日志
docker compose logs -f

# 只看最近 5 分钟的日志
docker compose logs --since=5m

# 搜索 aliyun 相关日志
docker compose logs | grep -i aliyun
```

### 8.2 PM2 日志

```bash
# 查看最近 100 行
pm2 logs clawrouter --lines 100

# 实时跟踪
pm2 logs clawrouter

# 清空日志
pm2 flush

# 日志文件位置
pm2 show clawrouter | grep "log path"
```

### 8.3 systemd 日志

```bash
# 查看最近 100 行
sudo journalctl -u clawrouter -n 100

# 实时跟踪
sudo journalctl -u clawrouter -f

# 查看最近 5 分钟
sudo journalctl -u clawrouter --since "5 minutes ago"

# 搜索关键词
sudo journalctl -u clawrouter | grep -i aliyun
```

### 8.4 关键日志内容

**成功的日志应包含**：

```
[INFO] ClawRouter v2.7.0 已启动
[INFO] 阿里云 Embedding: 已配置
[INFO] DASHSCOPE_API_KEY: 已配置
[INFO] 端口: 3000
```

**embedding 请求日志**：

```
[INFO] [Embedding] model=aliyun-embedding, valid_texts=1, mode=realtime
[INFO] [Aliyun Embedding] realtime sync 调用成功
```

或

```
[INFO] [Embedding] model=aliyun-embedding, valid_texts=3, mode=batch
[INFO] [Aliyun Embedding] async batch 调用成功, task_id=xxx
```

---

## 九、回滚到 v2.6.0

### 9.1 快速回滚（如果有备份）

#### Docker Compose 场景

```bash
# SSH 登录远程服务器
cd /opt/clawrouter

# 恢复备份文件
sudo cp backups/v2.6.0/server.js src/
sudo cp backups/v2.6.0/protocol-adapter.js src/
sudo cp backups/v2.6.0/.env . 2>/dev/null || true

# 重启服务
docker compose restart

# 验证版本
curl -s http://192.168.88.27:3000/health | jq '.version'
# 预期输出："2.6.0"
```

#### PM2 场景

```bash
# SSH 登录远程服务器
cd /opt/clawrouter

# 恢复备份文件
sudo cp backups/v2.6.0/server.js src/
sudo cp backups/v2.6.0/protocol-adapter.js src/
sudo cp backups/v2.6.0/.env . 2>/dev/null || true

# 重启服务
pm2 restart clawrouter

# 验证版本
curl -s http://192.168.88.27:3000/health | jq '.version'
# 预期输出："2.6.0"
```

### 9.2 从本地重新上传 v2.6.0

如果没有备份，从其他位置获取 v2.6.0 代码：

```bash
# 在本地执行
# 假设你有 v2.6.0 的备份在某个地方
scp /path/to/server.js.v2.6.0 \
    user@192.168.88.27:/opt/clawrouter/src/server.js

scp /path/to/protocol-adapter.js.v2.6.0 \
    user@192.168.88.27:/opt/clawrouter/src/protocol-adapter.js

# 然后重启服务
```

### 9.3 验证回滚成功

```bash
# 检查版本
curl -s http://192.168.88.27:3000/health | jq '.version'
# 预期输出："2.6.0"

# 检查 embeddings 字段
curl -s http://192.168.88.27:3000/health | jq '.embeddings'
# 预期输出：null

# 检查 models 列表
curl -s http://192.168.88.27:3000/v1/models | jq '.data[] | select(.id | contains("aliyun"))'
# 预期输出：无
```

---

## 十、故障排查

### 10.1 版本仍为 2.6.0

**可能原因**：
- 文件未上传成功
- 服务未重启
- 缓存问题

**解决方法**：
```bash
# 检查文件内容
head -15 /opt/clawrouter/src/server.js | grep "v2.7.0"

# 强制重启
docker compose down
docker compose up -d

# 或
pm2 delete clawrouter
pm2 start clawrouter
```

### 10.2 环境变量未生效

**可能原因**：
- .env 文件未配置
- Docker Compose 未重新加载
- systemd 环境变量未更新

**解决方法**：
```bash
# 检查环境变量
docker compose exec clawrouter env | grep DASHSCOPE

# 重新加载 Docker Compose
docker compose down
docker compose up -d

# 或 systemd
sudo systemctl daemon-reload
sudo systemctl restart clawrouter
```

### 10.3 API Key 无效

**错误信息**：
```json
{"error": "DASHSCOPE_API_KEY 未配置"}
```

**解决方法**：
```bash
# 检查 API Key 是否设置
cat .env | grep DASHSCOPE_API_KEY

# 测试 API Key 有效性
curl -s https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-v4", "input": "测试"}'
```

### 10.4 Batch 任务超时

**错误信息**：
```json
{"error": "Batch 任务超时: task_id=xxx, elapsed=300000ms"}
```

**解决方法**：
```bash
# 检查网络连接
ping dashscope.aliyuncs.com

# 检查阿里云服务状态
# 访问 https://status.aliyun.com/

# 增加超时时间（修改 server.js）
# pollTimeout: 600000  // 从 5 分钟改为 10 分钟
```

### 10.5 服务无法启动

**检查日志**：
```bash
# Docker Compose
docker compose logs --tail=50

# PM2
pm2 logs clawrouter --lines 50

# systemd
sudo journalctl -u clawrouter -n 50
```

**常见错误**：
- `EADDRINUSE: address already in use :::3000` → 端口被占用
- `Cannot find module './protocol-adapter'` → 文件缺失
- `SyntaxError` → 代码语法错误

---

## 十一、部署检查清单

### 部署前

- [ ] 本地代码版本确认为 v2.7.0
- [ ] AliyunEmbeddingProvider 类存在
- [ ] 远程服务状态正常（v2.6.0）
- [ ] 已准备 DASHSCOPE_API_KEY
- [ ] 已通知相关人员维护窗口

### 部署中

- [ ] 已备份 v2.6.0 文件
- [ ] 已上传 server.js
- [ ] 已上传 protocol-adapter.js
- [ ] 已配置环境变量
- [ ] 已重启服务

### 部署后

- [ ] 版本号确认为 2.7.0
- [ ] /health 显示 aliyun 配置
- [ ] /v1/models 显示 aliyun-embedding
- [ ] 单条文本 embedding 测试通过
- [ ] 多条文本 embedding 测试通过
- [ ] 空输入返回 400
- [ ] 全空白返回 400
- [ ] Voyage 共存测试通过
- [ ] 日志无异常错误

### 验收完成

- [ ] 所有测试用例通过
- [ ] 性能符合预期
- [ ] 文档已更新
- [ ] 监控告警正常

---

## 十二、联系方式

**部署支持**：
- ClawRouter 仓库：[待补充]
- 技术文档：`workspace/memory/kb/lessons/aliyun-embedding.md`
- 部署指南：`workspace/projects/clawrouter-v2.7.0-aliyun-embedding.md`

**紧急回滚**：
```bash
cd /opt/clawrouter
sudo cp backups/v2.6.0/* src/
docker compose restart  # 或 pm2 restart clawrouter
```

---

**文档版本**: v1.0
**更新日期**: 2026-03-15
**状态**: ready for deployment
