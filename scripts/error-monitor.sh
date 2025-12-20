#!/bin/bash
# Monitor de erros do Next.js para Claude Code
# Filtra apenas erros e os salva em arquivo separado

LOG_FILE="/tmp/claude/-root/tasks/b2fbf30.output"
ERROR_FILE="/tmp/nextjs-errors.log"
LAST_LINE_FILE="/tmp/nextjs-monitor-lastline"

# Inicializar arquivo de última linha
if [ ! -f "$LAST_LINE_FILE" ]; then
    echo "0" > "$LAST_LINE_FILE"
fi

while true; do
    if [ -f "$LOG_FILE" ]; then
        LAST_LINE=$(cat "$LAST_LINE_FILE")
        CURRENT_LINES=$(wc -l < "$LOG_FILE")

        if [ "$CURRENT_LINES" -gt "$LAST_LINE" ]; then
            # Pegar novas linhas e filtrar erros
            tail -n +$((LAST_LINE + 1)) "$LOG_FILE" | grep -iE "(error|Error|ERROR|TypeError|ReferenceError|SyntaxError|\[stderr\]|failed|Failed|FAILED|exception|Exception|warning|Warning|⨯)" >> "$ERROR_FILE"

            echo "$CURRENT_LINES" > "$LAST_LINE_FILE"
        fi
    fi
    sleep 2
done
