const vscode = require('vscode');
const WebSocket = require('ws');

function activate(context) {
    const ws = new WebSocket('ws://localhost:8765');

    ws.on('message', (message) => {
        const msg = JSON.parse(message);

        if (msg.type === 'diagnosis' && msg.recipient === 'Cursor') {
            msg.payload.files.forEach(f => {
                const filePath = f.path;
                const lines = f.lines;

                vscode.workspace.openTextDocument(filePath).then(doc => {
                    vscode.window.showTextDocument(doc).then(editor => {
                        lines.forEach(line => {
                            const range = new vscode.Range(line-1, 0, line-1, 100);
                            editor.selection = new vscode.Selection(range.start, range.end);
                            editor.revealRange(range, vscode.TextEditorRevealType.InCenter);
                        });
                    });
                });
            });
        }
    });

    console.log("Cursor Listener conectado al MCP.");
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
