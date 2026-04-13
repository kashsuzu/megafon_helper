#!/bin/bash

# Скрипт развертывания Megafon Helper в Docker
# Этот скрипт управляет установкой Docker, загрузкой/сборкой образа и запуском контейнера

set -e

# Конфигурация
IMAGE_NAME="flikxzr/megafon-helper"
IMAGE_TAG="latest"
CONTAINER_NAME="megafon-helper-bot"
SCRIPT_DIR="."
REPO_URL="https://github.com/kashsuzu/megafon_helper.git"
RAW_REPO_URL="https://raw.githubusercontent.com/kashsuzu/megafon_helper/master"
BIN_PATH="/usr/local/bin/megafonHelper"
DATA_DIR="$HOME/megafon_helper_data"


# Проверка и установка скрипта в /usr/local/bin/
install_to_bin() {
    if ! command -v megafonHelper &> /dev/null; then
        print_status "Устанавливаю megafonHelper в $BIN_PATH..."

        # Скачиваем скрипт в временный файл
        local temp_file=$(mktemp)
        if curl -fsSL "$RAW_REPO_URL/megafonHelper.sh" -o "$temp_file"; then
            sudo mv "$temp_file" "$BIN_PATH"
            sudo chmod +x "$BIN_PATH"
            print_success "megafonHelper установлен. Теперь можно запускать: megafonHelper"
        else
            print_warning "Не удалось установить megafonHelper в $BIN_PATH"
            rm -f "$temp_file"
        fi
    fi
}

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Без цвета

# Функция для вывода информационного сообщения
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Отображение стартового баннера
display_banner() {
    cat << "EOF"
███╗   ███╗███████╗ ██████╗  █████╗ ███████╗ ██████╗ ███╗   ██╗
████╗ ████║██╔════╝██╔════╝ ██╔══██╗██╔════╝██╔═══██╗████╗  ██║
██╔████╔██║█████╗  ██║  ███╗███████║█████╗  ██║   ██║██╔██╗ ██║
██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║██╔══╝  ██║   ██║██║╚██╗██║
██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║██║     ╚██████╔╝██║ ╚████║
╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═══╝
                                                                                                                                                   
     🌐 Разработчик: https://t.me/the_dth

EOF
}

# Проверка установки Docker
check_docker() {
    print_status "Проверяю установку Docker..."

    if ! command -v docker &> /dev/null; then
        print_warning "Docker не установлен"
        return 1
    fi

    print_success "Docker установлен"
    return 0
}

# Настройка Docker registry mirrors
configure_docker_mirrors() {
    print_status "Проверяю конфигурацию Docker registry mirrors..."

    local docker_config="$HOME/.docker/config.json"
    local mirror_url="https://mirror.gcr.io/"
    local needs_update=false

    # Создаем директорию если её нет
    mkdir -p "$HOME/.docker"

    # Если файла нет, создаем его с нужной конфигурацией
    if [ ! -f "$docker_config" ]; then
        print_status "Создаю конфиг Docker с registry mirrors..."
        cat > "$docker_config" << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.gcr.io/"
  ]
}
EOF
        needs_update=true
    else
        # Проверяем наличие registry-mirrors в конфиге
        if ! grep -q "registry-mirrors" "$docker_config"; then
            print_status "Добавляю registry-mirrors в конфиг Docker..."
            # Используем jq если доступен, иначе добавляем вручную
            if command -v jq &> /dev/null; then
                jq '.["registry-mirrors"] = ["https://mirror.gcr.io/"]' "$docker_config" > "$docker_config.tmp"
                mv "$docker_config.tmp" "$docker_config"
            else
                # Простое добавление перед закрывающей скобкой
                sed -i '$ s/}/,\n  "registry-mirrors": [\n    "https:\/\/mirror.gcr.io\/"\n  ]\n}/' "$docker_config"
            fi
            needs_update=true
        elif ! grep -q "https://mirror.gcr.io/" "$docker_config"; then
            print_status "Обновляю registry-mirrors в конфиге Docker..."
            if command -v jq &> /dev/null; then
                jq '.["registry-mirrors"] = ["https://mirror.gcr.io/"]' "$docker_config" > "$docker_config.tmp"
                mv "$docker_config.tmp" "$docker_config"
            else
                sed -i 's|"registry-mirrors": \[.*\]|"registry-mirrors": [\n    "https://mirror.gcr.io/"\n  ]|' "$docker_config"
            fi
            needs_update=true
        fi
    fi

    if [ "$needs_update" = true ]; then
        print_status "Перезагружаю Docker сервис..."
        if sudo systemctl reload docker.service; then
            print_success "Docker registry mirrors настроены"
        else
            print_error "Не удалось перезагрузить Docker сервис"
            return 1
        fi
    else
        print_success "Docker registry mirrors уже настроены"
    fi
}

# Установка Docker, если он не установлен
install_docker() {
    print_status "Устанавливаю Docker..."

    # Обновление менеджера пакетов
    print_status "Обновляю менеджер пакетов..."
    sudo apt update

    # Установка зависимостей
    print_status "Устанавливаю зависимости..."
    sudo apt install -y ca-certificates curl

    # Добавление официального GPG ключа Docker
    print_status "Добавляю GPG ключ Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Настройка репозитория Docker
    print_status "Настраиваю репозиторий Docker..."
    sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

    # Обновление менеджера пакетов
    print_status "Обновляю менеджер пакетов..."
    sudo apt update

    # Установка Docker
    print_status "Устанавливаю Docker и Docker Compose..."
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Добавление текущего пользователя в группу docker
    print_status "Добавляю текущего пользователя в группу docker..."
    sudo usermod -aG docker $USER

    # Включение сервиса Docker
    print_status "Включаю сервис Docker..."
    sudo systemctl enable docker
    sudo systemctl start docker

    print_success "Docker успешно установлен"
    print_warning "Пожалуйста, выйдите и войдите заново на сервер , чтобы изменения группы вступили в силу."
}

# Запрос токена бота у пользователя
request_bot_token() {
    print_status "Требуется токен бота для запуска приложения"

    while true; do
        read -p "🔑 Введите токен Telegram бота: " BOT_TOKEN

        if [ -z "$BOT_TOKEN" ]; then
            print_error "Токен бота не может быть пустым"
            continue
        fi

        break
    done
}

# Попытка загрузить образ с Docker Hub
pull_image() {
    print_status "Пытаюсь загрузить Docker образ: $IMAGE_NAME:$IMAGE_TAG"

    if docker pull "$IMAGE_NAME:$IMAGE_TAG" 2>/dev/null; then
        print_success "Образ успешно загружен"
        return 0
    else
        print_warning "Не удалось загрузить образ с Docker Hub"
        return 1
    fi
}

# Сборка образа из Dockerfile
build_image() {
    print_status "Собираю Docker образ из Dockerfile..."

    if [ ! -f "$SCRIPT_DIR/Dockerfile" ]; then
        print_status "Скачиваю репозиторий для сборки из исходников..."
        local src_dir="$HOME/megafon_helper_src"

        # Если директория уже существует, используем её
        if [ -d "$src_dir" ]; then
            print_status "Обновляю существующий репозиторий..."
            cd "$src_dir"
            git pull
            cd - > /dev/null
        else
            # Иначе клонируем новый
            if git clone "$REPO_URL" "$src_dir"; then
                print_success "Репозиторий скачан в $src_dir"
            else
                print_error "Не удалось скачать репозиторий"
                exit 1
            fi
        fi

        SCRIPT_DIR="$src_dir"
    fi

    if [ ! -f "$SCRIPT_DIR/Dockerfile" ]; then
        print_error "Dockerfile не найден в $SCRIPT_DIR"
        exit 1
    fi

    if docker build -t "$IMAGE_NAME:$IMAGE_TAG" "$SCRIPT_DIR"; then
        print_success "Образ успешно собран"
        return 0
    else
        print_error "Не удалось собрать Docker образ"
        exit 1
    fi
}

# Остановка и удаление существующего контейнера
cleanup_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_status "Останавливаю и удаляю существующий контейнер..."
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
        print_success "Контейнер удален"
    fi
}

# Проверка статуса контейнера
check_container_status() {
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        return 0  # Контейнер запущен
    elif docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        return 1  # Контейнер существует, но не запущен
    else
        return 2  # Контейнер не существует
    fi
}

# Отображение статуса контейнера
display_container_status() {
    set +e
    check_container_status
    local status=$?
    set -e

    echo ""
    if [ $status -eq 0 ]; then
        print_success "Контейнер запущен"
        docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        print_warning "Контейнер не запущен"
    fi
    echo ""
}

# Просмотр логов контейнера
view_logs() {
    set +e
    check_container_status
    local status=$?
    set -e

    if [ $status -eq 0 ]; then
        print_status "Просмотр логов контейнера (Ctrl+C для выхода)..."
        docker logs -f "$CONTAINER_NAME"
    else
        print_warning "Контейнер не запущен"
    fi
}

# Меню выбора действий
show_action_menu() {
    echo "Выберите действие:"
    echo "1. Скачать из Docker Hub и запустить"
    echo "2. Собрать из исходников и запустить"
    echo "3. Запустить существующий контейнер"
    echo "4. Остановить и удалить контейнер"
    echo "5. Просмотр логов"
    echo "6. Выход"
    echo ""
    read -p "Введите номер действия (1-6): " action_choice
}

# Запуск контейнера
start_container() {
    print_status "Запускаю Docker контейнер..."

    # Создание директорий для volumes если их нет
    mkdir -p "$DATA_DIR"

    if docker run -d \
        --name "$CONTAINER_NAME" \
        -e BOT_TOKEN="$BOT_TOKEN" \
        -e TZ=Europe/Moscow\
        -v "$DATA_DIR:/app/data" \
        --restart always\
        "$IMAGE_NAME:$IMAGE_TAG"; then

        print_success "Контейнер успешно запущен"
        print_status "Имя контейнера: $CONTAINER_NAME"
        print_status "Просмотр логов: docker logs -f $CONTAINER_NAME"
        print_status "Данные синхронизируются в: $DATA_DIR"
        return 0
    else
        print_error "Не удалось запустить контейнер"
        return 1
    fi
}

# Остановка контейнера
stop_container() {
    set +e
    check_container_status
    local status=$?
    set -e

    if [ $status -eq 0 ]; then
        print_status "Останавливаю контейнер..."
        if docker stop "$CONTAINER_NAME"; then
            print_success "Контейнер остановлен"
        else
            print_error "Не удалось остановить контейнер"
        fi
    else
        print_warning "Контейнер не запущен"
    fi
}

# Запуск существующего контейнера
restart_container() {
    set +e
    check_container_status
    local status=$?
    set -e

    if [ $status -eq 1 ]; then
        print_status "Запускаю существующий контейнер..."
        if docker start "$CONTAINER_NAME"; then
            print_success "Контейнер запущен"
        else
            print_error "Не удалось запустить контейнер"
        fi
    elif [ $status -eq 0 ]; then
        print_warning "Контейнер уже запущен"
    else
        print_error "Контейнер не существует"
    fi
}

# Основное выполнение
main() {
    mkdir -p "$DATA_DIR"

    # Установка скрипта в /usr/local/bin/ если нужно
    install_to_bin

    # Отображение стартового баннера
    display_banner

    # Проверка установки Docker
    if ! check_docker; then
        install_docker
    fi

    # Настройка Docker registry mirrors (одно сообщение и выполнение)
    configure_docker_mirrors

    # Отображение статуса контейнера
    display_container_status

    # Меню выбора действий
    while true; do
        show_action_menu

        case $action_choice in
            1)
                # Скачать из Docker Hub и запустить
                request_bot_token
                if pull_image; then
                    cleanup_container
                    start_container
                else
                    print_warning "Попытаюсь собрать образ из исходников..."
                    build_image
                    cleanup_container
                    start_container
                fi
                ;;
            2)
                # Собрать из исходников и запустить
                request_bot_token
                build_image
                cleanup_container
                start_container
                ;;
            3)
                # Запустить существующий контейнер
                set +e
                check_container_status
                local status=$?
                set -e
                if [ $status -eq 1 ]; then
                    restart_container
                elif [ $status -eq 0 ]; then
                    print_warning "Контейнер уже запущен"
                else
                    print_error "Контейнер не существует. Выберите другое действие."
                fi
                ;;
            4)
                # Остановить и удалить контейнер
                stop_container
                cleanup_container
                ;;
            5)
                # Просмотр логов
                view_logs
                ;;
            6)
                # Выход
                print_status "Выход из программы"
                exit 0
                ;;
            *)
                print_error "Неверный выбор. Пожалуйста, введите число от 1 до 6."
                ;;
        esac
    done

}

# Запуск основной функции
main
