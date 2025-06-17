# MCP Feedback Enhanced

**🌐 Language / 語言切換:** **English** | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

**Original Author:** [Fábio Ferreira](https://x.com/fabiomlferreira) | [Original Project](https://github.com/noopstudios/interactive-feedback-mcp) ⭐
**Enhanced Fork:** [Minidoracat](https://github.com/Minidoracat)
**UI Design Reference:** [sanshao85/mcp-feedback-collector](https://github.com/sanshao85/mcp-feedback-collector)

## 🎯 Core Concept

This is an [MCP server](https://modelcontextprotocol.io/) that establishes **feedback-oriented development workflows**, providing **Web UI and Desktop Application** dual interface options, perfectly adapting to local, **SSH Remote environments** (Cursor SSH Remote, VS Code Remote SSH), and **WSL (Windows Subsystem for Linux) environments**. By guiding AI to confirm with users rather than making speculative operations, it can consolidate multiple tool calls into a single feedback-oriented request, dramatically reducing platform costs and improving development efficiency.

**🌐 Dual Interface Architecture Advantages:**
- 🖥️ **Desktop Application**: Native cross-platform desktop experience, supporting Windows, macOS, Linux
- 🌐 **Web UI Interface**: No GUI dependencies required, suitable for remote and WSL environments
- 🔧 **Flexible Deployment**: Choose the most suitable interface mode based on environment requirements
- 📦 **Unified Functionality**: Both interfaces provide exactly the same functional experience

**🖥️ Desktop Application:** v2.5.0 introduces cross-platform desktop application support based on Tauri framework, supporting Windows, macOS, and Linux platforms with native desktop experience.

**Supported Platforms:** [Cursor](https://www.cursor.com) | [Cline](https://cline.bot) | [Windsurf](https://windsurf.com) | [Augment](https://www.augmentcode.com) | [Trae](https://www.trae.ai)

### 🔄 Workflow
1. **AI Call** → `mcp-feedback-enhanced` tool
2. **Interface Launch** → Auto-open desktop application or browser interface (based on configuration)
3. **Smart Interaction** → Prompt selection, text input, image upload, auto-submit
4. **Real-time Feedback** → WebSocket connection delivers information to AI instantly
5. **Session Tracking** → Auto-record session history and statistics
6. **Process Continuation** → AI adjusts behavior or ends task based on feedback

## 🌟 Key Features

### 🖥️ Dual Interface Support
- **Desktop Application**: Cross-platform native application based on Tauri, supporting Windows, macOS, Linux
- **Web UI Interface**: Lightweight browser interface suitable for remote and WSL environments
- **Automatic Environment Detection**: Intelligently recognizes SSH Remote, WSL and other special environments
- **Unified Feature Experience**: Both interfaces provide exactly the same functionality

### 📝 Smart Workflow
- **Prompt Management**: CRUD operations for common prompts, usage statistics, intelligent sorting
- **Auto-Timed Submit**: 1-86400 second flexible timer, supports pause, resume, cancel
- **Session Management & Tracking**: Local file storage, privacy controls, history export, real-time statistics
- **Connection Monitoring**: WebSocket status monitoring, auto-reconnection, quality indicators
- **AI Work Summary Markdown Display**: Support for rich Markdown syntax rendering including headers, bold text, code blocks, lists, links and other formats for enhanced content readability

### 🎨 Modern Experience
- **Responsive Design**: Adapts to different screen sizes, modular JavaScript architecture
- **Audio Notifications**: Built-in multiple sound effects, custom audio upload support, volume control
- **Smart Memory**: Input box height memory, one-click copy, persistent settings
- **Multi-language Support**: Traditional Chinese, English, Simplified Chinese, instant switching

### 🖼️ Images & Media
- **Full Format Support**: PNG, JPG, JPEG, GIF, BMP, WebP
- **Convenient Upload**: Drag & drop files, clipboard paste (Ctrl+V)
- **Unlimited Processing**: Support for any size images, automatic intelligent processing

## 🌐 Interface Preview

### Web UI Interface (v2.5.0 - Desktop Application Support)

<div align="center">
  <img src="docs/en/images/web1.jpeg" width="400" alt="Web UI Main Interface - Prompt Management & Auto Submit" />
</div>

<details>
<summary>📱 Click to view complete interface screenshots</summary>

<div align="center">
  <img src="docs/en/images/web2.jpeg" width="800" alt="Web UI Complete Interface - Session Management & Settings" />
</div>

</details>

*Web UI Interface - Supports desktop application and Web interface, providing prompt management, auto-submit, session tracking and other smart features*

### Desktop Application Interface (v2.5.0 New Feature)

<div align="center">
  <img src="docs/en/images/desktop1.png" width="600" alt="Desktop Application - Native Cross-platform Desktop Experience" />
</div>

*Desktop Application - Native cross-platform desktop application based on Tauri framework, supporting Windows, macOS, Linux with exactly the same functionality as Web UI*

**Shortcut Support**
- `Ctrl+Enter`（Windows/Linux）/ `Cmd+Enter`（macOS）：Submit feedback (both main keyboard and numeric keypad supported)
- `Ctrl+V`（Windows/Linux）/ `Cmd+V`（macOS）：Direct paste clipboard images
- `Ctrl+I`（Windows/Linux）/ `Cmd+I`（macOS）：Quick focus input box (Thanks @penn201500)

## 🚀 Quick Start

### 1. Installation & Testing
```bash
# Install uv (if not already installed)
pip install uv

# Quick test
uvx mcp-feedback-enhanced@latest test
```

### 2. Configure MCP
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

**Advanced Configuration** (requires custom environment):
```json
{
  "mcpServers": {
    "mcp-feedback-enhanced": {
      "command": "uvx",
      "args": ["mcp-feedback-enhanced@latest"],
      "timeout": 600,
      "env": {
        "MCP_DEBUG": "false",
        "MCP_WEB_PORT": "8765"
      },
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

**Desktop Application Configuration** (v2.5.0 new feature - using native desktop application):
```json
{
  "mcpServers": {
    "mcp-feedback-enhanced": {
      "command": "uvx",
      "args": ["mcp-feedback-enhanced@latest"],
      "timeout": 600,
      "env": {
        "MCP_DESKTOP_MODE": "true",
        "MCP_WEB_PORT": "8765",
        "MCP_DEBUG": "false"
      },
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```

**Configuration File Examples**:
- Desktop Mode: [examples/mcp-config-desktop.json](examples/mcp-config-desktop.json)
- Web Mode: [examples/mcp-config-web.json](examples/mcp-config-web.json)

### 3. Prompt Engineering Setup
For optimal results, add the following rules to your AI assistant:

```
# MCP Interactive Feedback Rules

follow mcp-feedback-enhanced instructions
```

## ⚙️ Advanced Settings

### Environment Variables
| Variable | Purpose | Values | Default |
|----------|---------|--------|---------|
| `MCP_DEBUG` | Debug mode | `true`/`false` | `false` |
| `MCP_WEB_PORT` | Web UI port | `1024-65535` | `8765` |
| `MCP_DESKTOP_MODE` | Desktop application mode | `true`/`false` | `false` |

### Testing Options
```bash
# Version check
uvx mcp-feedback-enhanced@latest version       # Check version

# Interface testing
uvx mcp-feedback-enhanced@latest test --web    # Test Web UI (auto continuous running)
uvx mcp-feedback-enhanced@latest test --desktop # Test desktop application (v2.5.0 new feature)

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
# Functional testing
make test-func                                           # Standard functional testing
make test-web                                            # Web UI testing (continuous running)
make test-desktop-func                                   # Desktop application functional testing

# Or use direct commands
uv run python -m mcp_feedback_enhanced test              # Standard functional testing
uvx --no-cache --with-editable . mcp-feedback-enhanced test --web   # Web UI testing (continuous running)
uvx --no-cache --with-editable . mcp-feedback-enhanced test --desktop # Desktop application testing

# Desktop application build (v2.5.0 new feature)
make build-desktop                                       # Build desktop application (debug mode)
make build-desktop-release                               # Build desktop application (release mode)
make test-desktop                                        # Test desktop application
make clean-desktop                                       # Clean desktop build artifacts

# Unit testing
make test                                                # Run all unit tests
make test-fast                                          # Fast testing (skip slow tests)
make test-cov                                           # Test and generate coverage report

# Code quality checks
make check                                              # Complete code quality check
make quick-check                                        # Quick check and auto-fix
```

**Testing Descriptions**
- **Functional Testing**: Test complete MCP tool functionality workflow
- **Unit Testing**: Test individual module functionality
- **Coverage Testing**: Generate HTML coverage report to `htmlcov/` directory
- **Quality Checks**: Include linting, formatting, type checking

## 🆕 Version History

📋 **Complete Version History:** [RELEASE_NOTES/CHANGELOG.md](RELEASE_NOTES/CHANGELOG.md)

### Latest Version Highlights (v2.5.0)
- 🖥️ **Desktop Application**: Brand new cross-platform desktop application supporting Windows, macOS, Linux
- 📋 **AI Work Summary Markdown Display**: Support for Markdown syntax rendering including headers, bold text, code blocks, lists, links and other formats
- ⚡ **Significant Performance Enhancement**: Introduced debounce/throttle mechanisms to reduce unnecessary rendering and network requests
- 📊 **Session History Storage Improvement**: Migrated from localStorage to server-side local file storage
- 🌐 **Network Connection Stability**: Improved WebSocket reconnection mechanism with network status detection
- 🎨 **UI Rendering Optimization**: Optimized rendering performance for session management, statistics, and status indicators
- 🛠️ **Build Process Optimization**: Added Makefile desktop application build commands and development tools
- 📚 **Documentation Enhancement**: Added desktop application build guide and workflow documentation

## 🐛 Common Issues

### 🌐 SSH Remote Environment Issues
**Q: Browser cannot launch in SSH Remote environment**
A: This is normal. SSH Remote environments have no graphical interface, requiring manual opening in local browser. For detailed solutions, refer to: [SSH Remote Environment Usage Guide](docs/en/ssh-remote/browser-launch-issues.md)

**Q: Why am I not receiving new MCP feedback?**
A: Likely a WebSocket connection issue. **Solution**: Directly refresh the browser page.

**Q: Why isn't MCP being called?**
A: Please confirm MCP tool status shows green light. **Solution**: Repeatedly toggle MCP tool on/off, wait a few seconds for system reconnection.

**Q: Augment cannot start MCP**
A: **Solution**: Completely close and restart VS Code or Cursor, reopen the project.

### 🔧 General Issues
**Q: How to use desktop application?**
A: v2.5.0 introduces cross-platform desktop application support. Set `"MCP_DESKTOP_MODE": "true"` in MCP configuration to enable:
```json
{
  "mcpServers": {
    "mcp-feedback-enhanced": {
      "command": "uvx",
      "args": ["mcp-feedback-enhanced@latest"],
      "timeout": 600,
      "env": {
        "MCP_DESKTOP_MODE": "true",
        "MCP_WEB_PORT": "8765"
      },
      "autoApprove": ["interactive_feedback"]
    }
  }
}
```
**Configuration File Example**: [examples/mcp-config-desktop.json](examples/mcp-config-desktop.json)

**Q: How to use legacy PyQt6 GUI interface?**
A: v2.4.0 completely removed PyQt6 GUI dependencies. To use legacy GUI, specify v2.3.0 or earlier: `uvx mcp-feedback-enhanced@2.3.0`
**Note**: Legacy versions don't include new features (prompt management, auto-submit, session management, desktop application, etc.).

**Q: "Unexpected token 'D'" error appears**
A: Debug output interference. Set `MCP_DEBUG=false` or remove the environment variable.

**Q: Chinese character garbled text**
A: Fixed in v2.0.3. Update to latest version: `uvx mcp-feedback-enhanced@latest`

**Q: Window disappears or positioning errors in multi-screen environment**
A: Fixed in v2.1.1. Go to "⚙️ Settings" tab, check "Always show window at primary screen center" to resolve. Especially suitable for T-shaped screen arrangements and other complex multi-screen configurations.

**Q: Image upload failure**
A: Check file format (PNG/JPG/JPEG/GIF/BMP/WebP). System supports any size image files.

**Q: Web UI cannot start**
A: Check firewall settings or try using different ports.

**Q: UV Cache occupies too much disk space**
A: Due to frequent use of `uvx` commands, cache may accumulate to tens of GB. Regular cleanup recommended:
```bash
# View cache size and detailed information
python scripts/cleanup_cache.py --size

# Preview cleanup content (no actual cleanup)
python scripts/cleanup_cache.py --dry-run

# Execute standard cleanup
python scripts/cleanup_cache.py --clean

# Force cleanup (attempts to close related programs, solving Windows file occupation issues)
python scripts/cleanup_cache.py --force

# Or directly use uv command
uv cache clean
```
For detailed instructions, refer to: [Cache Management Guide](docs/en/cache-management.md)

**Q: AI models cannot parse images**
A: Various AI models (including Gemini Pro 2.5, Claude, etc.) may have instability in image parsing, sometimes correctly recognizing and sometimes unable to parse uploaded image content. This is a known limitation of AI visual understanding technology. Recommendations:
1. Ensure good image quality (high contrast, clear text)
2. Try uploading multiple times, retries usually succeed
3. If parsing continues to fail, try adjusting image size or format

## 🙏 Acknowledgments

### 🌟 Support Original Author
**Fábio Ferreira** - [X @fabiomlferreira](https://x.com/fabiomlferreira)
**Original Project:** [noopstudios/interactive-feedback-mcp](https://github.com/noopstudios/interactive-feedback-mcp)

If you find it useful, please:
- ⭐ [Star the original project](https://github.com/noopstudios/interactive-feedback-mcp)
- 📱 [Follow the original author](https://x.com/fabiomlferreira)

### Design Inspiration
**sanshao85** - [mcp-feedback-collector](https://github.com/sanshao85/mcp-feedback-collector)

### Contributors
**penn201500** - [GitHub @penn201500](https://github.com/penn201500)
- 🎯 Auto-focus input box feature ([PR #39](https://github.com/Minidoracat/mcp-feedback-enhanced/pull/39))

### Community Support
- **Discord:** [https://discord.gg/Gur2V67](https://discord.gg/Gur2V67)
- **Issues:** [GitHub Issues](https://github.com/Minidoracat/mcp-feedback-enhanced/issues)

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Minidoracat/mcp-feedback-enhanced&type=Date)](https://star-history.com/#Minidoracat/mcp-feedback-enhanced&Date)

---
**🌟 Welcome to Star and share with more developers!**
