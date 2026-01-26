import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

app.registerExtension({
	name: "SequentialBatcher.DisplayBatch",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "LoadCSV" || nodeData.name === "PreviewBatch") {
			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);
				if (message?.text) {
					const text = message.text[0];
					let widget = this.widgets.find((w) => w.name === "batch_preview");
					if (!widget) {
						widget = ComfyWidgets["STRING"](this, "batch_preview", ["STRING", { multiline: true }], app).widget;
						widget.inputEl.readOnly = true;
						widget.inputEl.style.fontFamily = "monospace";
						widget.inputEl.style.fontSize = "10px";
						widget.inputEl.style.overflowY = "scroll";
					}
					widget.value = text;
					this.onResize?.(this.size);
				}
			};
		}
	}
});
