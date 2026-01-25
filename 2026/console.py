import io

class ConsoleRedirector(io.TextIOBase):
    def __init__(self, text_widget):
        self.text_widget = text_widget
        # Tags for colors
        self.text_widget.tag_config("error", foreground="#ff4c4c")
        self.text_widget.tag_config("warning", foreground="#ffc107")
        self.text_widget.tag_config("download", foreground="#4cff4c")
        self.text_widget.tag_config("ffmpeg", foreground="#4ca6ff")
        self.text_widget.tag_config("extract", foreground="#da70d6")
        self.text_widget.tag_config("info", foreground="#aaaaaa")
        self.text_widget.tag_config("complete", foreground="#00ffff")
        self.text_widget.tag_config("default", foreground="#ffffff")

    def write(self, message):
        self.text_widget.after(0, self._write, message)

    def _write(self, message):
        if "\r" in message:
            self.text_widget.delete("end-2l", "end-1l")
            message = message.split("\r")[-1]
        tag = self.get_tag_for_line(message)
        self.text_widget.insert("end", message, tag)
        self.text_widget.see("end")

    def get_tag_for_line(self, message):
        lowered = message.lower()
        if "[error]" in lowered or "error" in lowered or "exception" in lowered:
            return "error"
        elif "[warning]" in lowered or "warning" in lowered:
            return "warning"
        elif "[download]" in lowered or "downloading" in lowered:
            return "download"
        elif "[ffmpeg]" in lowered:
            return "ffmpeg"
        elif "[extractaudio]" in lowered or "destination:" in lowered:
            return "extract"
        elif "complete" in lowered or "deleting original file" in lowered:
            return "complete"
        elif "[youtube]" in lowered or "[info]" in lowered:
            return "info"
        else:
            return "default"

    def flush(self):
        pass

class YTDLRedirectLogger:
    def __init__(self, redirector):
        self.redirector = redirector

    def debug(self, msg):
        self.redirector.write(msg + "\n")

    def warning(self, msg):
        self.redirector.write("WARNING: " + msg + "\n")

    def error(self, msg):
        self.redirector.write("ERROR: " + msg + "\n")
