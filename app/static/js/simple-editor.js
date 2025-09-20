/**
 * 简化富文本编辑器
 * 替代TinyMCE，提供基本的富文本编辑功能
 */

class SimpleEditor {
    constructor(selector, options = {}) {
        this.selector = selector;
        this.element = typeof selector === 'string' ? document.querySelector(selector) : selector;
        this.options = {
            height: options.height || '300px',
            placeholder: options.placeholder || '请输入内容...',
            toolbar: options.toolbar !== false,
            ...options
        };

        if (this.element) {
            this.init();
        }
    }

    init() {
        this.createEditor();
        this.bindEvents();
    }

    createEditor() {
        // 创建编辑器容器
        this.container = document.createElement('div');
        this.container.className = 'simple-editor';
        this.container.style.border = '1px solid #d1d5db';
        this.container.style.borderRadius = '6px';
        this.container.style.overflow = 'hidden';

        // 创建工具栏
        if (this.options.toolbar) {
            this.toolbar = document.createElement('div');
            this.toolbar.className = 'simple-editor-toolbar';
            this.toolbar.style.cssText = `
                background: #f9fafb;
                border-bottom: 1px solid #e5e7eb;
                padding: 8px 12px;
                display: flex;
                gap: 4px;
                flex-wrap: wrap;
            `;

            this.createToolbarButtons();
            this.container.appendChild(this.toolbar);
        }

        // 创建编辑区域
        this.editor = document.createElement('div');
        this.editor.contentEditable = true;
        this.editor.style.cssText = `
            min-height: ${this.options.height};
            padding: 12px;
            outline: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #374151;
        `;
        this.editor.innerHTML = this.element.value || '';

        // 设置placeholder
        if (!this.editor.textContent.trim()) {
            this.editor.innerHTML = `<p style="color: #9ca3af; margin: 0;">${this.options.placeholder}</p>`;
        }

        this.container.appendChild(this.editor);

        // 替换原始textarea
        this.element.style.display = 'none';
        this.element.parentNode.insertBefore(this.container, this.element.nextSibling);
    }

    createToolbarButtons() {
        const buttons = [
            { command: 'bold', icon: '𝗕', title: '粗体' },
            { command: 'italic', icon: '𝐼', title: '斜体' },
            { command: 'underline', icon: '𝑈', title: '下划线' },
            { type: 'separator' },
            { command: 'formatBlock', value: 'h1', text: 'H1', title: '标题1' },
            { command: 'formatBlock', value: 'h2', text: 'H2', title: '标题2' },
            { command: 'formatBlock', value: 'h3', text: 'H3', title: '标题3' },
            { command: 'formatBlock', value: 'p', text: '段落', title: '段落' },
            { type: 'separator' },
            { command: 'insertUnorderedList', icon: '•', title: '无序列表' },
            { command: 'insertOrderedList', icon: '1.', title: '有序列表' },
            { type: 'separator' },
            { command: 'justifyLeft', icon: '⊣', title: '左对齐' },
            { command: 'justifyCenter', icon: '⊢', title: '居中' },
            { command: 'justifyRight', icon: '⊤', title: '右对齐' },
            { type: 'separator' },
            { command: 'createLink', icon: '🔗', title: '插入链接' },
            { command: 'removeFormat', icon: '🚫', title: '清除格式' }
        ];

        buttons.forEach(btn => {
            if (btn.type === 'separator') {
                const separator = document.createElement('div');
                separator.style.cssText = 'width: 1px; height: 24px; background: #e5e7eb; margin: 0 4px;';
                this.toolbar.appendChild(separator);
                return;
            }

            const button = document.createElement('button');
            button.type = 'button';
            button.style.cssText = `
                background: none;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 8px;
                cursor: pointer;
                font-size: 12px;
                line-height: 1;
                color: #374151;
                min-width: 28px;
                height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
            `;
            button.innerHTML = btn.icon || btn.text;
            button.title = btn.title;

            button.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.execCommand(btn.command, btn.value);
            });

            button.addEventListener('mouseover', () => {
                button.style.background = '#e5e7eb';
            });

            button.addEventListener('mouseout', () => {
                button.style.background = 'none';
            });

            this.toolbar.appendChild(button);
        });
    }

    execCommand(command, value = null) {
        this.editor.focus();

        if (command === 'createLink') {
            const url = prompt('请输入链接地址:', 'https://');
            if (url) {
                document.execCommand(command, false, url);
            }
        } else {
            document.execCommand(command, false, value);
        }

        this.updateContent();
    }

    bindEvents() {
        // 内容变化时同步到原始textarea
        this.editor.addEventListener('input', () => {
            this.updateContent();
        });

        this.editor.addEventListener('keydown', (e) => {
            // Enter键处理
            if (e.key === 'Enter' && !e.shiftKey) {
                // 确保有段落标签
                setTimeout(() => {
                    const selection = window.getSelection();
                    if (selection.anchorNode && selection.anchorNode.nodeType === Node.TEXT_NODE) {
                        const p = document.createElement('p');
                        const range = selection.getRangeAt(0);
                        range.surroundContents(p);
                    }
                }, 10);
            }
        });

        // 聚焦时清除placeholder
        this.editor.addEventListener('focus', () => {
            if (this.editor.innerHTML.includes(this.options.placeholder)) {
                this.editor.innerHTML = '<p><br></p>';
                const range = document.createRange();
                const sel = window.getSelection();
                range.setStart(this.editor.firstChild, 0);
                range.collapse(true);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        });

        // 失焦时恢复placeholder
        this.editor.addEventListener('blur', () => {
            if (!this.editor.textContent.trim()) {
                this.editor.innerHTML = `<p style="color: #9ca3af; margin: 0;">${this.options.placeholder}</p>`;
            }
            this.updateContent();
        });
    }

    updateContent() {
        const content = this.editor.innerHTML;
        // 清理空的placeholder
        const cleanContent = content.includes(this.options.placeholder) && !this.editor.textContent.trim()
            ? ''
            : content;
        this.element.value = cleanContent;

        // 触发change事件，便于Alpine.js监听
        this.element.dispatchEvent(new Event('input'));
    }

    getContent() {
        return this.element.value;
    }

    setContent(content) {
        this.editor.innerHTML = content || `<p style="color: #9ca3af; margin: 0;">${this.options.placeholder}</p>`;
        this.updateContent();
    }

    destroy() {
        if (this.container && this.container.parentNode) {
            this.container.parentNode.removeChild(this.container);
        }
        this.element.style.display = '';
    }
}

// 全局对象，模拟TinyMCE API
window.tinymce = {
    editors: new Map(),

    init(config) {
        const selector = config.selector;
        const element = document.querySelector(selector);

        if (element) {
            // 销毁已存在的编辑器
            this.remove(selector);

            const editor = new SimpleEditor(element, {
                height: config.height || '300px',
                placeholder: '详细的新闻内容...支持基本的富文本格式'
            });

            // 扩展编辑器对象以匹配TinyMCE API
            editor.getContent = () => editor.element.value;
            editor.setContent = (content) => {
                editor.editor.innerHTML = content || `<p style="color: #9ca3af; margin: 0;">${editor.options.placeholder}</p>`;
                editor.updateContent();
            };
            editor.destroy = () => editor.destroy();

            // 触发init事件
            if (config.setup) {
                const mockEditor = {
                    on: (event, callback) => {
                        if (event === 'init') {
                            setTimeout(callback, 100);
                        } else if (event === 'input change keyup') {
                            editor.editor.addEventListener('input', callback);
                        }
                    },
                    getContent: () => editor.getContent(),
                    setContent: (content) => editor.setContent(content)
                };
                config.setup(mockEditor);
            }

            this.editors.set(selector.replace('#', ''), editor);
        }
    },

    get(id) {
        return this.editors.get(id);
    },

    remove(selector) {
        const id = typeof selector === 'string' ? selector.replace('#', '') : selector;
        const editor = this.editors.get(id);
        if (editor) {
            editor.destroy();
            this.editors.delete(id);
        }
    }
};

// 确保全局可用
window.SimpleEditor = SimpleEditor;