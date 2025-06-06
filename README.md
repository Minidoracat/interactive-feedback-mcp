# MCP Feedback Enhanced

**Original Author:** [Fábio Ferreira](https://x.com/fabiomlferreira) | [Original Project](https://github.com/noopstudios/interactive-feedback-mcp) ⭐
**Enhanced Fork:** [Minidoracat](https://github.com/Minidoracat)
**UI Design Reference:** [sanshao85/mcp-feedback-collector](https://github.com/sanshao85/mcp-feedback-collector)

## 🎯 Core Concept

This is an [MCP server](https://modelcontextprotocol.io/) that establishes **feedback-oriented development workflows**, primarily using a **Web UI**, making it suitable for local, **SSH remote development environments**, and **WSL (Windows Subsystem for Linux) environments**. By guiding AI to confirm with users rather than making speculative operations, it can consolidate multiple tool calls into a single feedback-oriented request, dramatically reducing platform costs and improving development efficiency.

**Supported Platforms:** [Cursor](https://www.cursor.com) | [Cline](https://cline.bot) | [Windsurf](https://windsurf.com) | [Augment](https://www.augmentcode.com) | [Trae](https://www.trae.ai)

### 🔄 Workflow
1. **AI Call** → `mcp-feedback-enhanced`
2. **Web UI Launch** → Interface for user interaction
3. **User Interaction** → Command execution, text feedback, image upload
4. **Feedback Delivery** → Information returns to AI
5. **Process Continuation** → Adjust or end based on feedback

## 🌟 Key Features

### 🎨 Web Interface Design
- **Modular Architecture**: Web UI adopts a modular design for maintainability.
- **Centralized Management**: Reorganized folder structure for easier maintenance.
- **Modern Themes**: Improved visual design and user experience.
- **Responsive Layout**: Adapts to different screen sizes and window dimensions.

### 🖼️ Image Support
- **Format Support**: PNG, JPG, JPEG, GIF, BMP, WebP
- **Upload Methods**: Drag & drop files + clipboard paste (Ctrl+V)
- **Auto Processing**: Smart compression to ensure 1MB limit compliance

### ✨ WSL Environment Support
- **Auto Detection**: Intelligently identifies WSL (Windows Subsystem for Linux) environments.
- **Browser Integration**: Automatically launches Windows browser in WSL environments.
- **Multiple Launch Methods**: Supports `cmd.exe`, `powershell.exe`, `wslview` and other browser launch methods.
- **Seamless Experience**: WSL users can directly use Web UI without additional configuration.

## 🖥️ Interface Preview

### Web UI Interface
<div align="center">
  <img src="https://raw.githubusercontent.com/Minidoracat/mcp-feedback-enhanced/main/docs/en/images/web1.png" width="400" alt="Web UI Main Interface" />
  <img src="https://raw.githubusercontent.com/Minidoracat/mcp-feedback-enhanced/main/docs/en/images/web2.png" width="400" alt="Web UI Settings Interface" />
</div>

*Web UI Interface - Modern architecture, suitable for local, SSH Remote, and WSL environments*

**Keyboard Shortcuts**
- `Ctrl+Enter` (Windows/Linux) / `Cmd+Enter` (macOS): Submit feedback
- `Ctrl+V` (Windows/Linux) / `Cmd+V` (macOS): Directly paste clipboard images

## 🚀 Quick Start

### 1. Installation & Testing
```bash
# Install uv (if not already installed)
pip install uv

# Quick test
uvx mcp-feedback-enhanced@latest test
```

### 2. MCP Configuration
**Basic Configuration** (suitable for most users):
```json
{
  "mcpServers": {
    "mcp-feedback-enhanced": {
      "command": "uvx",
      "args": ["mcp-feedback-enhanced@latest"],
      "timeout": 600,
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

**Advanced Configuration** (custom environment needed):
```json
{
  "mcpServers": {
    "mcp-feedback-enhanced": {
      "command": "uvx",
      "args": ["mcp-feedback-enhanced@latest"],
      "timeout": 600,
      "env": {
        "MCP_DEBUG": "false"
      },
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

### 3. Prompt Engineering Setup
For best results, add these rules to your AI assistant:

```
# MCP Interactive Feedback Rules

1. During any process, task, or conversation, whether asking, responding, or completing stage tasks, must call MCP mcp-feedback-enhanced.
2. When receiving user feedback, if feedback content is not empty, must call MCP mcp-feedback-enhanced again and adjust behavior based on feedback.
3. Only when user explicitly indicates "end" or "no more interaction needed" can you stop calling MCP mcp-feedback-enhanced, then the process is complete.
4. Unless receiving end command, all steps must repeatedly call MCP mcp-feedback-enhanced.
5. Before completing the task, use the MCP mcp-feedback-enhanced to ask the user for feedback.
```

## ⚙️ Advanced Settings

### Environment Variables
| Variable | Purpose | Values | Default |
|----------|---------|--------|---------|
| `MCP_DEBUG` | Debug mode | `true`/`false` | `false` |

### Testing Options
```bash
# Version check
uvx mcp-feedback-enhanced@latest version       # Check version

# Test Web UI (auto continuous running, this is the default test)
uvx mcp-feedback-enhanced@latest test

# Debug mode
MCP_DEBUG=true uvx mcp-feedback-enhanced@latest test
```

### Developer Installation
```bash
git clone https://github.com/Minidoracat/mcp-feedback-enhanced.git
cd mcp-feedback-enhanced
uv sync
```

**Local Testing Methods**
```bash
# Method 1: Standard test (recommended)
uv run python -m mcp_feedback_enhanced test

# Method 2: Complete test suite (macOS and Windows dev environment)
uvx --with-editable . mcp-feedback-enhanced test

# Method 3: Test Web UI (default test for editable install)
uvx --with-editable . mcp-feedback-enhanced test
```

**Testing Descriptions**
- **Standard Test**: Complete functionality check, suitable for daily development verification.
- **Complete Test**: Deep testing of all components, suitable for pre-release verification.
- **Web UI Test**: Start Web server and keep running for complete Web functionality testing.

## 🆕 Version History

### Latest Version Highlights (v2.2.5)
- ✨ **WSL Environment Support**: Added comprehensive support for WSL (Windows Subsystem for Linux) environments
- 🌐 **Smart Browser Launching**: Automatically invokes Windows browser in WSL environments with multiple launch methods
- 🎯 **Environment Detection Optimization**: Improved remote environment detection logic, WSL no longer misidentified as remote environment
- 🧪 **Testing Experience Improvement**: Test mode automatically attempts browser launching for better testing experience

## 🐛 Common Issues

**Q: Getting "Unexpected token 'D'" error**
A: Debug output interference. Set `MCP_DEBUG=false` or remove the environment variable.

**Q: Chinese character garbled text**
A: Fixed in v2.0.3. Update to latest version: `uvx mcp-feedback-enhanced@latest`

**Q: Image upload fails**
A: Check file size (≤1MB) and format (PNG/JPG/GIF/BMP/WebP).

**Q: Web UI won't start**
A: Check firewall settings or if the port is already in use.

**Q: UV Cache taking up too much disk space**
A: Due to frequent use of `uvx` commands, cache may accumulate to tens of GB. Regular cleanup is recommended:
```bash
# Check cache size and detailed information
python scripts/cleanup_cache.py --size

# Preview cleanup content (without actually cleaning)
python scripts/cleanup_cache.py --dry-run

# Execute standard cleanup
python scripts/cleanup_cache.py --clean

# Force cleanup (attempts to close related processes, solves Windows file lock issues)
python scripts/cleanup_cache.py --force

# Or use uv command directly
uv cache clean
```

**Q: Gemini Pro 2.5 cannot parse images**
A: Known issue. Gemini Pro 2.5 may not correctly parse uploaded image content. Testing shows Claude-4-Sonnet can properly analyze images. Recommend using Claude models for better image understanding capabilities.

**Q: Cannot launch browser in WSL environment**
A: v2.2.5 has added WSL environment support. If issues persist:
1. Confirm WSL version (WSL 2 recommended)
2. Check if Windows browser is properly installed
3. Try manual test: run `cmd.exe /c start https://www.google.com` in WSL
4. If `wslu` package is installed, you can also try the `wslview` command

**Q: WSL environment misidentified as remote environment**
A: v2.2.5 has fixed this issue. WSL environments are now correctly identified and use Web UI with Windows browser launching, instead of being misidentified as remote environments.

## 🙏 Acknowledgments

### 🌟 Support Original Author
**Fábio Ferreira** - [X @fabiomlferreira](https://x.com/fabiomlferreira)
**Original Project:** [noopstudios/interactive-feedback-mcp](https://github.com/noopstudios/interactive-feedback-mcp)

If you find this useful, please:
- ⭐ [Star the original project](https://github.com/noopstudios/interactive-feedback-mcp)
- 📱 [Follow the original author](https://x.com/fabiomlferreira)

### Design Inspiration
**sanshao85** - [mcp-feedback-collector](https://github.com/sanshao85/mcp-feedback-collector)