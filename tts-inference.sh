#!/bin/bash
set -e

# TTS Inference Wrapper Script
# Handles optional dependency installation based on selected model

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_usage() {
    echo "Usage: $0 --model {chatterbox|qwen} [ARGS...]"
    echo ""
    echo "Required:"
    echo "  --model MODEL    Select TTS model: 'chatterbox' or 'qwen'"
    echo ""
    echo "All remaining arguments are passed to main.py"
    echo ""
    echo "Examples:"
    echo "  $0 --model qwen --help"
    echo "  $0 --model chatterbox start-server --model chatterbox"
    echo "  $0 --model qwen start-server --model qwen"
    exit 1
}

# Parse model argument
MODEL=""
REMAINING_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            if [[ -n "$MODEL" ]]; then
                echo -e "${RED}Error: --model specified multiple times${NC}"
                show_usage
            fi
            MODEL="$2"
            shift 2
            ;;
        *)
            REMAINING_ARGS+=("$1")
            shift
            ;;
    esac
done

# Validate model selection
if [[ -z "$MODEL" ]]; then
    echo -e "${RED}Error: --model argument is required${NC}"
    show_usage
fi

if [[ "$MODEL" != "chatterbox" && "$MODEL" != "qwen" ]]; then
    echo -e "${RED}Error: Invalid model '$MODEL'. Must be 'chatterbox' or 'qwen'${NC}"
    show_usage
fi

echo -e "${GREEN}Selected model: $MODEL${NC}"

# Use separate venvs for each model due to conflicting transformers versions
VENV_DIR=".venv-$MODEL"

# Check if dependencies are already installed
NEED_SYNC=false
if [[ "$MODEL" == "chatterbox" ]]; then
    if ! "$VENV_DIR/bin/python" -c "import chatterbox_tts" 2>/dev/null; then
        NEED_SYNC=true
    fi
elif [[ "$MODEL" == "qwen" ]]; then
    if ! "$VENV_DIR/bin/python" -c "import qwen_tts" 2>/dev/null; then
        NEED_SYNC=true
    fi
fi

# Sync dependencies if needed
if [[ "$NEED_SYNC" == true ]]; then
    echo -e "${YELLOW}Installing $MODEL dependencies...${NC}"
    # Create venv if it doesn't exist
    if [[ ! -d "$VENV_DIR" ]]; then
        uv venv "$VENV_DIR" --python 3.11
    fi
    
    # For qwen, install PyTorch with matching CUDA version first
    if [[ "$MODEL" == "qwen" ]]; then
        # Detect system CUDA version
        if command -v nvcc &> /dev/null; then
            CUDA_VERSION=$(nvcc --version 2>&1 | grep "release" | sed -n 's/.*release \([0-9]*\.[0-9]*\).*/\1/p')
            CUDA_MAJOR=$(echo "$CUDA_VERSION" | cut -d. -f1)
            CUDA_MINOR=$(echo "$CUDA_VERSION" | cut -d. -f2)
            echo -e "${GREEN}Detected CUDA $CUDA_VERSION${NC}"
            
            # Map to PyTorch CUDA version (cu130 for CUDA 13.x)
            if [[ "$CUDA_MAJOR" == "13" ]]; then
                TORCH_CUDA="cu130"
            elif [[ "$CUDA_MAJOR" == "12" ]]; then
                TORCH_CUDA="cu128"
            elif [[ "$CUDA_MAJOR" == "11" ]]; then
                TORCH_CUDA="cu118"
            else
                echo -e "${YELLOW}Warning: Unsupported CUDA version $CUDA_VERSION, using cu130${NC}"
                TORCH_CUDA="cu130"
            fi
            
            echo -e "${YELLOW}Installing PyTorch with $TORCH_CUDA support...${NC}"
            TORCH_INDEX_URL="https://download.pytorch.org/whl/$TORCH_CUDA"
            
            # Install torch and torchaudio with matching CUDA version first
            uv pip install --python "$VENV_DIR" \
                --index-url "$TORCH_INDEX_URL" \
                "torch>=2.1.0" "torchaudio>=2.1.0"
            
            echo -e "${GREEN}PyTorch with $TORCH_CUDA installed${NC}"
        else
            echo -e "${RED}Warning: nvcc not found, installing default PyTorch${NC}"
        fi
        
        # Install rest of dependencies including flash-attn
        # Set environment variables to ensure flash-attn builds against correct CUDA
        echo -e "${YELLOW}Installing model dependencies (including flash-attn)...${NC}"
        
        # Find CUDA_HOME by locating nvcc
        NVCC_PATH=$(which nvcc)
        if [[ -n "$NVCC_PATH" ]]; then
            export CUDA_HOME="$(dirname $(dirname $NVCC_PATH))"
            echo -e "${GREEN}Found CUDA at: $CUDA_HOME${NC}"
        else
            # Fallback to common locations
            for cuda_path in "/opt/cuda" "/usr/local/cuda-${CUDA_MAJOR}.${CUDA_MINOR}" "/usr/local/cuda"; do
                if [[ -d "$cuda_path" ]]; then
                    export CUDA_HOME="$cuda_path"
                    break
                fi
            done
        fi
        
        if [[ -z "$CUDA_HOME" ]] || [[ ! -d "$CUDA_HOME" ]]; then
            echo -e "${RED}Error: Could not find CUDA installation${NC}"
            exit 1
        fi
        
        export PATH="$CUDA_HOME/bin:$PATH"
        export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
        
        # Force flash-attn to use the installed PyTorch's CUDA
        export FLASH_ATTENTION_FORCE_BUILD=TRUE
        export MAX_JOBS=4  # Limit parallel jobs to avoid OOM
        
        # Install dependencies except flash-attn first
        echo -e "${YELLOW}Installing dependencies (excluding flash-attn)...${NC}"
        uv pip install --python "$VENV_DIR" -e "." --no-deps
        uv pip install --python "$VENV_DIR" \
            "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0" "websockets>=13.0" \
            "pyzmq>=26.0" "click>=8.1.0" "pydantic>=2.0" "python-multipart>=0.0.9" \
            "aiosqlite>=0.20.0" "onnxruntime<1.20.0" "onnx<1.17" "ml_dtypes<0.5" \
            "setuptools>=80.9.0" "peft>=0.18.0" "librosa>=0.10.0" "pyworld>=0.3.4" \
            "crepe>=0.0.13" "scipy>=1.11.0" "msgpack>=1.0.0" "qwen-tts>=0.0.5"
        
        # Now install flash-attn without build isolation to use our PyTorch
        echo -e "${GREEN}Building flash-attn for CUDA $CUDA_VERSION (CUDA_HOME=$CUDA_HOME)...${NC}"
        uv pip install --python "$VENV_DIR" --no-build-isolation "flash-attn>=2.0.0"
    else
        # For chatterbox, normal installation
        uv pip install --python "$VENV_DIR" -e ".[$MODEL]"
    fi
else
    echo -e "${GREEN}$MODEL dependencies already installed${NC}"
fi

# Run main.py with all remaining arguments using the model-specific venv
# Set TTS_MODEL environment variable to match selected model
export CHATTERBOX_TTS_MODEL="$MODEL"
echo -e "${GREEN}Running: python main.py ${REMAINING_ARGS[*]}${NC}"
source "$VENV_DIR/bin/activate"
python main.py "${REMAINING_ARGS[@]}"
