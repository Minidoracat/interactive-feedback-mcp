# 🎯 MCP Feedback Enhanced

A modern MCP feedback collection system with real-time web interface and file upload support. Built with FastAPI + Vue.js 3 + WebSocket for seamless user experience.

## ✨ Features

- 🚀 **Real-time Communication**: WebSocket-based live feedback collection
- 📁 **File Upload Support**: Image upload with processing and validation
- 🎨 **Modern Web Interface**: Vue.js 3 + Vite responsive design
- 🔌 **MCP Protocol Compatible**: Full `collect_feedback` tool implementation
- ⚡ **Session Management**: Automatic lifecycle and cleanup
- 📦 **One-click Deployment**: uvx support for instant usage

## 🚀 Quick Start

### Using uvx (Recommended)

```bash
# Install and run in one command
uvx mcp-feedback-enhanced serve

# Or with custom options
uvx mcp-feedback-enhanced serve --port 8080 --host 0.0.0.0
```

### Traditional Installation

```bash
# Install from PyPI
pip install mcp-feedback-enhanced

# Start the server
mcp-feedback-enhanced serve
```

## 🛠️ Development

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Minidoracat/mcp-feedback-enhanced.git
cd mcp-feedback-enhanced

# Install dependencies
pdm install

# Start development server
pdm run dev
```

### Frontend Development

```bash
# Navigate to frontend development directory
cd frontend-dev

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📖 Usage

### Basic Usage

1. Start the server:
   ```bash
   mcp-feedback-enhanced serve
   ```

2. Open your browser and navigate to `http://localhost:8000`

3. Use the web interface to collect feedback with optional file uploads

### MCP Integration

The system provides a `collect_feedback` tool that can be used by MCP clients:

```python
# Example MCP client usage
from mcp import Client

client = Client("mcp-feedback-enhanced")
result = await client.call_tool("collect_feedback", {
    "session_id": "feedback_20241207_abc123",
    "feedback_text": "This is my feedback",
    "images": ["base64_encoded_image_data"]
})
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │   Web Browser   │    │   CLI Tool      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   MCP Server    │  WebSocket      │     REST API                │
│   Protocol      │  Handler        │     Endpoints               │
└─────────────────┴─────────────────┴─────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Session Manager                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Memory Store   │  File Handler   │   Config Manager            │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables

- `MCP_FEEDBACK_HOST`: Server host (default: `127.0.0.1`)
- `MCP_FEEDBACK_PORT`: Server port (default: `8000`)
- `MCP_FEEDBACK_SESSION_TIMEOUT`: Session timeout in seconds (default: `3600`)
- `MCP_FEEDBACK_MAX_FILE_SIZE`: Maximum file size in bytes (default: `10485760`)

### Configuration File

Create a `config.json` file in your working directory:

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "session_timeout": 3600,
  "max_file_size": 10485760,
  "allowed_file_types": ["image/jpeg", "image/png", "image/gif"]
}
```

## 🧪 Testing

```bash
# Run all tests
pdm run test

# Run with coverage
pdm run test-cov

# Run specific test file
pytest tests/test_backend/test_session.py -v
```

## 📝 API Documentation

Once the server is running, visit:
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Vue.js](https://vuejs.org/) - Progressive JavaScript framework
- [MCP](https://github.com/modelcontextprotocol/python-sdk) - Model Context Protocol
- [Uvicorn](https://www.uvicorn.org/) - Lightning-fast ASGI server

## 📞 Support

- 📧 Email: contact@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/Minidoracat/mcp-feedback-enhanced/issues)
- 📖 Documentation: [GitHub Wiki](https://github.com/Minidoracat/mcp-feedback-enhanced/wiki)