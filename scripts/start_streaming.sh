#!/bin/bash
# SIEM Real-time Streaming Service

PIDFILE=/tmp/bolcd_streaming.pid
LOGFILE=/var/log/bolcd_streaming.log

start() {
    if [ -f $PIDFILE ]; then
        echo "⚠️ Streaming already running (PID: $(cat $PIDFILE))"
        exit 1
    fi
    
    echo "🚀 Starting SIEM streaming service..."
    nohup python /home/yoshi/workspace/BOL-CD/scripts/siem_connector.py \
        --source splunk \
        --mode stream \
        --interval 300 \
        --config /home/yoshi/workspace/BOL-CD/config/siem_config.json \
        >> $LOGFILE 2>&1 &
    
    echo $! > $PIDFILE
    echo "✅ Streaming started (PID: $(cat $PIDFILE))"
}

stop() {
    if [ ! -f $PIDFILE ]; then
        echo "⚠️ Streaming not running"
        exit 1
    fi
    
    PID=$(cat $PIDFILE)
    echo "🛑 Stopping streaming (PID: $PID)..."
    kill $PID
    rm -f $PIDFILE
    echo "✅ Streaming stopped"
}

status() {
    if [ -f $PIDFILE ]; then
        PID=$(cat $PIDFILE)
        if ps -p $PID > /dev/null; then
            echo "✅ Streaming running (PID: $PID)"
            tail -5 $LOGFILE
        else
            echo "⚠️ PID file exists but process not running"
            rm -f $PIDFILE
        fi
    else
        echo "❌ Streaming not running"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
