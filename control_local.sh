#!/bin/bash
CONFIG="/root/.openclaw/workspace/local_instance_config.json"
HOST=$(jq -r '.local_instance.host' "$CONFIG")
PORT=$(jq -r '.local_instance.port' "$CONFIG")
TOKEN=$(jq -r '.local_instance.token' "$CONFIG")

case $1 in
    "start")
        curl -s -X POST -H "Authorization: Bearer $TOKEN" -d '{"message":"start"}' "https://$HOST:$PORT/api/sessions" > /dev/null
        echo "本地实例启动命令已发送"
        ;;
    "send")
        shift
        COMMAND="$*"
        curl -s -X POST -H "Authorization: Bearer $TOKEN" -d "{\"message\":\"$COMMAND\"}" "https://$HOST:$PORT/api/sessions" > /dev/null
        echo "命令已发送: $COMMAND"
        ;;
    "status")
        STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" "https://$HOST:$PORT/api/health" | grep -o "openclaw-app" || echo "offline")
        echo "本地实例状态: $STATUS"
        ;;
    *)
        echo "用法: $0 {start|send|status}"
        ;;
esac