#!/bin/bash

# Megafon Helper - главный скрипт для управления приложением
# Проверяет наличие исходников, скачивает если нужно, запускает run.sh

set -e

REPO_URL="https://github.com/kashsuzu/megafon_helper.git"
SRC_DIR="$HOME/megafon_helper_src"

# Проверка и клонирование репозитория если нужно
ensure_repo() {
    if [ ! -d "$SRC_DIR" ]; then
        echo "📥 Скачиваю репозиторий в $SRC_DIR..."
        git clone "$REPO_URL" "$SRC_DIR"
    else
        echo "🔄 Обновляю исходники в $SRC_DIR..."
        cd "$SRC_DIR"
        git pull origin master
        cd - > /dev/null
    fi
}

# Основное выполнение
main() {
    ensure_repo

    # Запускаем run.sh из исходников
    bash "$SRC_DIR/run.sh" "$@"
}

main "$@"
