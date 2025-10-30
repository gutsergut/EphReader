# Makefile for Swiss Ephemeris DLL (MinGW-w64)
# Компилирует все C файлы в swedll64.dll

CC = gcc
CFLAGS = -O3 -Wall -DWIN32 -D_WINDOWS -D_USRDLL -fPIC
LDFLAGS = -shared -Wl,--out-implib,libswe.a

SRC_DIR = vendor/swisseph/pyswisseph-2.10.3.2/libswe
BUILD_DIR = build/swisseph
DLL_NAME = vendor/swisseph/swedll64.dll

# Все C файлы из libswe
SOURCES = $(wildcard $(SRC_DIR)/*.c)
OBJECTS = $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SOURCES))

.PHONY: all clean test

all: $(DLL_NAME)

$(DLL_NAME): $(OBJECTS)
	@echo "Linking DLL..."
	$(CC) $(LDFLAGS) -o $@ $^ -lm
	@echo "✅ Swiss Ephemeris DLL compiled: $(DLL_NAME)"

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c
	@mkdir -p $(BUILD_DIR)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR) $(DLL_NAME) vendor/swisseph/libswe.a
	@echo "Cleaned build artifacts"

test:
	@echo "Testing DLL..."
	@if [ -f $(DLL_NAME) ]; then \
		echo "✅ DLL exists: $(DLL_NAME)"; \
		ls -lh $(DLL_NAME); \
	else \
		echo "❌ DLL not found"; \
	fi

help:
	@echo "Swiss Ephemeris DLL Build"
	@echo ""
	@echo "Usage:"
	@echo "  make        - Compile DLL"
	@echo "  make clean  - Remove build artifacts"
	@echo "  make test   - Test if DLL exists"
	@echo ""
	@echo "Requirements:"
	@echo "  - MinGW-w64 (gcc)"
	@echo "  - pyswisseph source in vendor/swisseph/"
