/**
 * Monaco Editor Setup - CodePulse
 * Initializes the editor and exposes helpers used by the main app.
 */

let editor = null;

function initMonacoEditor() {
    return new Promise((resolve) => {
        require.config({
            paths: {
                vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs",
            },
        });

        require(["vs/editor/editor.main"], function () {
            monaco.editor.defineTheme("codepulse-nexus", {
                base: "vs-dark",
                inherit: true,
                rules: [
                    { token: "comment", foreground: "6a9955", fontStyle: "italic" },
                    { token: "keyword", foreground: "c586c0" },
                    { token: "string", foreground: "ce9178" },
                    { token: "number", foreground: "b5cea8" },
                    { token: "type", foreground: "4ec9b0" },
                    { token: "function", foreground: "dcdcaa" },
                    { token: "variable", foreground: "9cdcfe" },
                    { token: "operator", foreground: "d4d4d4" },
                    { token: "delimiter", foreground: "d4d4d4" },
                ],
                colors: {
                    "editor.background": "#0a0a0f",
                    "editor.foreground": "#d4d4d4",
                    "editor.lineHighlightBackground": "#ffffff0a",
                    "editor.selectionBackground": "#264f78",
                    "editorCursor.foreground": "#aeafad",
                    "editor.selectionHighlightBackground": "#add6ff26",
                    "editorLineNumber.foreground": "#858585",
                    "editorLineNumber.activeForeground": "#c6c6c6",
                    "editorIndentGuide.background": "#ffffff08",
                    "editorIndentGuide.activeBackground": "#ffffff12",
                    "editor.inactiveSelectionBackground": "#00d4ff0a",
                    "editorWidget.background": "#0c0c14",
                    "editorWidget.border": "#ffffff0f",
                    "input.background": "#0c0c14",
                    "input.border": "#ffffff0f",
                    "scrollbar.shadow": "#00000000",
                    "scrollbarSlider.background": "#ffffff0d",
                    "scrollbarSlider.hoverBackground": "#ffffff1a",
                    "scrollbarSlider.activeBackground": "#ffffff26",
                },
            });

            const sampleCode = `# Welcome to CodePulse!
# Paste your Python code here or start writing.

def fibonacci(n):
    """Generate the first n Fibonacci numbers."""
    if n <= 0:
        return []

    sequence = [0, 1]
    while len(sequence) < n:
        sequence.append(sequence[-1] + sequence[-2])

    return sequence[:n]


def is_prime(num):
    """Check if a number is prime."""
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True


result = fibonacci(10)
print("Fibonacci:", result)
print("Primes:", [x for x in range(20) if is_prime(x)])`;

            let initialCode = sampleCode;
            // Session restoration removed as per user request

            editor = monaco.editor.create(document.getElementById("monaco-editor"), {
                value: initialCode,
                language: "python",
                theme: "codepulse-nexus",
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: 13.5,
                lineHeight: 22,
                padding: { top: 16 },
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                renderLineHighlight: "all",
                cursorBlinking: "smooth",
                cursorSmoothCaretAnimation: "on",
                smoothScrolling: true,
                bracketPairColorization: { enabled: true },
                autoClosingBrackets: "always",
                automaticLayout: true,
                tabSize: 4,
                wordWrap: "on",
                glyphMargin: false,
                folding: true,
                lineNumbersMinChars: 3,
                overviewRulerLanes: 0,
                hideCursorInOverviewRuler: true,
                overviewRulerBorder: false,
            });

            window.addEventListener("resize", layoutEditor);
            resolve(editor);
        });
    });
}

function getEditorCode() {
    return editor ? editor.getValue() : "";
}

function setEditorLanguage(lang) {
    if (!editor) return;
    const model = editor.getModel();
    if (model) {
        monaco.editor.setModelLanguage(model, lang);
    }
}

function layoutEditor() {
    if (editor) {
        editor.layout();
    }
}
