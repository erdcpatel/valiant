#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"

echo "Project Root: $PROJECT_ROOT"

# Export PYTHONPATH to include the project root so valiant module can be found
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Create directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Function to start a service
start_service() {
    local service_name=$1
    local command=$2
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$PID_DIR/${service_name}.pid"

    echo -e "${BLUE}Starting $service_name...${NC}"
    echo -e "${BLUE}PYTHONPATH: $PYTHONPATH${NC}"

    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo -e "${YELLOW}$service_name is already running (PID: $(cat $pid_file))${NC}"
        return 1
    fi

    # Start the service in background with proper environment
    cd "$PROJECT_ROOT" && eval "$command" >> "$log_file" 2>&1 &
    local pid=$!

    # Save PID
    echo $pid > "$pid_file"

    # Wait a bit to check if service started successfully
    sleep 3
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}$service_name started successfully (PID: $pid)${NC}"
        echo -e "${GREEN}Logs: $log_file${NC}"
        return 0
    else
        echo -e "${RED}Failed to start $service_name${NC}"
        echo -e "${RED}Check logs: $log_file${NC}"
        rm -f "$pid_file"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${BLUE}Stopping $service_name (PID: $pid)...${NC}"
            kill $pid
            rm -f "$pid_file"
            echo -e "${GREEN}$service_name stopped${NC}"
        else
            echo -e "${YELLOW}$service_name not running, cleaning up PID file${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}$service_name is not running${NC}"
    fi
}

# Function to show status
status_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"

    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo -e "${GREEN}$service_name is running (PID: $(cat $pid_file))${NC}"
    else
        echo -e "${RED}$service_name is not running${NC}"
        # Clean up stale PID file
        [ -f "$pid_file" ] && rm -f "$pid_file"
    fi
}

# Function to tail logs
tail_logs() {
    local service_name=$1
    local log_file="$LOG_DIR/${service_name}.log"

    if [ -f "$log_file" ]; then
        echo -e "${BLUE}Tailing logs for $service_name:${NC}"
        tail -f "$log_file"
    else
        echo -e "${RED}Log file not found: $log_file${NC}"
    fi
}

#Main Execution
case "${1:-start}" in
    start)
        echo -e "${BLUE}Starting Valiant UI Services...${NC}"
        echo -e "${BLUE}Project Root: $PROJECT_ROOT${NC}"
        echo -e "${BLUE}Python Path: $PYTHONPATH${NC}"

        # Start FastAPI
        start_service "fastapi" "uvicorn valiant.ui.fastapi_app:app --host 0.0.0.0 --port 8000"

        # Start Streamlit
        start_service "streamlit" "streamlit run valiant/ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"

        echo -e "${GREEN}Services started!${NC}"
        echo -e "${GREEN}FastAPI:  http://localhost:8000${NC}"
        echo -e "${GREEN}Streamlit: http://localhost:8501${NC}"
        echo -e "${GREEN}Logs: $LOG_DIR/${NC}"
        ;;

    stop)
        echo -e "${BLUE}Stopping Valiant UI Services...${NC}"
        stop_service "streamlit"
        stop_service "fastapi"
        ;;

    restart)
        echo -e "${BLUE}Restarting Valiant UI Services...${NC}"
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        echo -e "${BLUE}Service Status:${NC}"
        status_service "fastapi"
        status_service "streamlit"
        ;;

    logs)
        case "${2:-}" in
            fastapi)
                tail_logs "fastapi"
                ;;
            streamlit)
                tail_logs "streamlit"
                ;;
            *)
                echo -e "${RED}Usage: $0 logs [fastapi|streamlit]${NC}"
                ;;
        esac
        ;;

    clean)
        echo -e "${BLUE}Cleaning log and PID files...${NC}"
        rm -rf "$LOG_DIR"/*.log
        rm -rf "$PID_DIR"/*.pid
        echo -e "${GREEN}Clean complete${NC}"
        ;;

    *)
        echo -e "${BLUE}Valiant UI Services Manager${NC}"
        echo -e "Usage: $0 {start|stop|restart|status|logs|clean}"
        echo -e "  start   - Start both services"
        echo -e "  stop    - Stop both services"
        echo -e "  restart - Restart both services"
        echo -e "  status  - Show service status"
        echo -e "  logs    - Tail logs (fastapi|streamlit)"
        echo -e "  clean   - Clean log and PID files"
        ;;
esac
