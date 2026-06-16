.PHONY: help install-backend install-frontend install-admin install start-backend start-frontend start-admin start docker

-include .env
export

BACKEND_PORT ?= 8081
FRONTEND_PORT ?= 8080
ADMIN_PORT ?= 8082

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' Makefile | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-24s\033[0m %s\n", $$1, $$2}'

.env: ## Tạo file .env từ .env.example nếu chưa có file .env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Đã tạo .env từ .env.example. Vui lòng cập nhật GEMINI_API_KEY trong .env để AI có thể phản hồi."; \
	fi

install-backend: ## Cài đặt thư viện cho Backend
	@echo "==> Cài đặt Backend"
	@cd backend && if [ ! -d ".venv" ]; then \
		if command -v python3.11 >/dev/null 2>&1; then python3.11 -m venv .venv; \
		else python3 -m venv .venv; fi \
	fi
	@cd backend && .venv/bin/python -m pip install --upgrade pip
	@cd backend && .venv/bin/python -m pip install -r requirements.txt

install-frontend: ## Cài đặt thư viện cho Frontend
	@echo "==> Cài đặt Frontend"
	@cd frontend && npm ci

install-admin: ## Cài đặt thư viện cho Admin
	@echo "==> Cài đặt Admin"
	@cd admin && npm ci

install: install-backend install-frontend install-admin ## Cài đặt thư viện cho TẤT CẢ các dự án

start-backend: .env ## Chạy duy nhất Backend
	@echo "==> Khởi động Backend tại http://127.0.0.1:$(BACKEND_PORT)"
	@cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port $(BACKEND_PORT) --env-file ../.env

start-frontend: .env ## Chạy duy nhất Frontend
	@echo "==> Khởi động Frontend tại http://localhost:$(FRONTEND_PORT)"
	@cd frontend && npm run dev

start-admin: .env ## Chạy duy nhất Admin
	@echo "==> Khởi động Admin tại http://localhost:$(ADMIN_PORT)"
	@cd admin && npm run dev

start: .env ## Chạy TẤT CẢ các dịch vụ cùng lúc (Local)
	@echo "==> Đang khởi động tất cả dịch vụ... (Bấm Ctrl+C để dừng)"
	@make -j3 start-backend start-frontend start-admin

docker: .env ## Chạy TẤT CẢ các dịch vụ bằng Docker
	@echo "==> Khởi động Docker"
	docker compose up -d --build
	@echo "Frontend: http://localhost:$(FRONTEND_PORT)"
	@echo "Admin:    http://localhost:$(ADMIN_PORT)"
	@echo "API docs: http://localhost:$(BACKEND_PORT)/api/v1/docs"
