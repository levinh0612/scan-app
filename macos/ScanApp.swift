// ScanApp.swift — cửa sổ ScanApp trên macOS (một icon duy nhất).
//   Chưa cài  → chạy cài đặt (qua Terminal thu nhỏ) và báo tiến độ.
//   Đã cài    → bật server ngầm nếu chưa chạy, rồi hiện QR + link cho điện thoại, nút mở app.
// Lưu ý macOS: app mở từ Finder không được đọc ~/Documents → mọi việc đụng thư mục dự án giao cho Terminal,
// app này chỉ nói chuyện với server qua HTTP và đọc file trạng thái trong /tmp.
import Cocoa

let ROOT: String = {   // đường dẫn thư mục scan-app do make-mac-app.sh ghi vào Resources/root.txt
    if let p = Bundle.main.path(forResource: "root", ofType: "txt"), let t = try? String(contentsOfFile: p, encoding: .utf8) {
        return t.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    return CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : ""
}()
let LOG = "/tmp/scanapp-start.log"

final class Trust: NSObject, URLSessionDelegate {   // chứng chỉ tự ký của chính máy này
    func urlSession(_ s: URLSession, didReceive c: URLAuthenticationChallenge,
                    completionHandler h: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if let t = c.protectionSpace.serverTrust { h(.useCredential, URLCredential(trust: t)) } else { h(.performDefaultHandling, nil) }
    }
}
let session = URLSession(configuration: .ephemeral, delegate: Trust(), delegateQueue: nil)

func fetch(_ url: String, timeout: TimeInterval = 2) -> Data? {   // chạy ở luồng nền
    guard let u = URL(string: url) else { return nil }
    var req = URLRequest(url: u); req.timeoutInterval = timeout
    let sem = DispatchSemaphore(value: 0); var out: Data?
    session.dataTask(with: req) { d, r, _ in
        if let h = r as? HTTPURLResponse, h.statusCode == 200 { out = d }; sem.signal()
    }.resume()
    _ = sem.wait(timeout: .now() + timeout + 1)
    return out
}

func findBase() -> String? {
    for p in 8000...8010 { for s in ["http", "https"] {
        if fetch("\(s)://localhost:\(p)/api/health", timeout: 1.5) != nil { return "\(s)://localhost:\(p)" }
    } }
    return nil
}

func startViaTerminal() {
    try? FileManager.default.removeItem(atPath: LOG)
    let sh = "cd '\(ROOT)' && { if [ -x .venv/bin/python ]; then echo '##START'; else echo '##INSTALL'; fi; ./run.sh --auto; echo \"##END $?\"; } 2>&1 | tee \(LOG); exit"
    let esc = sh.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
    let script = """
    tell application "Terminal"
      set w to do script "\(esc)"
      try
        set miniaturized of (first window whose selected tab is w) to true
      end try
    end tell
    """
    DispatchQueue.global().async {
        let p = Process(); p.launchPath = "/usr/bin/osascript"; p.arguments = ["-e", script]
        try? p.run(); p.waitUntilExit()
    }
}

func logInfo() -> (mode: String, last: String, endRC: Int?) {
    guard let raw = try? String(contentsOfFile: LOG, encoding: .utf8) else { return ("", "", nil) }
    let clean = raw.replacingOccurrences(of: "\u{1B}\\[[0-9;]*[A-Za-z]", with: "", options: .regularExpression)
    let lines = clean.components(separatedBy: .newlines).map { $0.trimmingCharacters(in: .whitespaces) }
    var mode = "", end: Int? = nil
    for l in lines {
        if l == "##START" { mode = "start" } else if l == "##INSTALL" { mode = "install" }
        if l.hasPrefix("##END") { end = Int(l.dropFirst(5).trimmingCharacters(in: .whitespaces)) ?? 1 }
    }
    let shown = lines.last { !$0.isEmpty && !$0.hasPrefix("##") && !$0.contains("█") && !$0.contains("▄") && !$0.contains("▀") } ?? ""
    return (mode, String(shown.prefix(90)), end)
}

func rounded(_ size: CGFloat, _ w: NSFont.Weight) -> NSFont {
    let f = NSFont.systemFont(ofSize: size, weight: w)
    if let d = f.fontDescriptor.withDesign(.rounded), let r = NSFont(descriptor: d, size: size) { return r }
    return f
}
func setBtn(_ b: NSButton, _ t: String, primary: Bool) {
    let ps = NSMutableParagraphStyle(); ps.alignment = .center
    b.attributedTitle = NSAttributedString(string: t, attributes: [.font: NSFont.systemFont(ofSize: 18, weight: .semibold),
        .foregroundColor: primary ? NSColor.white : NSColor.controlAccentColor, .paragraphStyle: ps])
}

final class App: NSObject, NSApplicationDelegate {
    var win: NSWindow!
    let status = NSTextField(wrappingLabelWithString: "")
    let detail = NSTextField(wrappingLabelWithString: "")
    let spinner = NSProgressIndicator()
    let qr = NSImageView()
    let caption = NSTextField(wrappingLabelWithString: "")
    let link = NSTextField(labelWithString: "")
    let card = NSView(), chip = NSView()
    let open = NSButton(title: "Mở app trên máy này", target: nil, action: nil)
    let copy = NSButton(title: "Chép link", target: nil, action: nil)
    let retry = NSButton(title: "Thử lại", target: nil, action: nil)
    var base: String?, shownURL = "", started = false, busy = false, startedAt = Date()

    func applicationDidFinishLaunching(_ n: Notification) {
        let m = NSMenu(); let ai = NSMenuItem(); m.addItem(ai)
        let sm = NSMenu(); sm.addItem(NSMenuItem(title: "Thoát ScanApp", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        ai.submenu = sm; NSApp.mainMenu = m

        win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 480, height: 700), styleMask: [.titled, .closable, .miniaturizable, .fullSizeContentView],
                       backing: .buffered, defer: false)
        win.title = "ScanApp"; win.center(); win.isReleasedWhenClosed = false
        win.titlebarAppearsTransparent = true; win.titleVisibility = .hidden
        let vev = NSVisualEffectView(); vev.material = .underWindowBackground; vev.blendingMode = .behindWindow; vev.state = .active
        win.contentView = vev

        let title = NSTextField(labelWithString: "ScanApp"); title.font = rounded(34, .bold)
        status.font = .systemFont(ofSize: 20, weight: .semibold); status.alignment = .center
        detail.font = .systemFont(ofSize: 14); detail.textColor = .secondaryLabelColor; detail.alignment = .center
        spinner.style = .bar; spinner.isIndeterminate = true; spinner.startAnimation(nil)
        qr.imageScaling = .scaleProportionallyUpOrDown; qr.isHidden = true
        card.wantsLayer = true; card.layer?.backgroundColor = NSColor.white.cgColor; card.layer?.cornerRadius = 28
        card.layer?.shadowColor = NSColor.black.cgColor; card.layer?.shadowOpacity = 0.18; card.layer?.shadowRadius = 20; card.layer?.shadowOffset = CGSize(width: 0, height: -6)
        card.isHidden = true; qr.translatesAutoresizingMaskIntoConstraints = false; card.addSubview(qr)
        NSLayoutConstraint.activate([card.widthAnchor.constraint(equalToConstant: 280), card.heightAnchor.constraint(equalToConstant: 280),
            qr.topAnchor.constraint(equalTo: card.topAnchor, constant: 16), qr.bottomAnchor.constraint(equalTo: card.bottomAnchor, constant: -16),
            qr.leadingAnchor.constraint(equalTo: card.leadingAnchor, constant: 16), qr.trailingAnchor.constraint(equalTo: card.trailingAnchor, constant: -16)])
        chip.wantsLayer = true; chip.layer?.backgroundColor = NSColor.labelColor.withAlphaComponent(0.07).cgColor; chip.layer?.cornerRadius = 12
        chip.isHidden = true; link.translatesAutoresizingMaskIntoConstraints = false; chip.addSubview(link)
        NSLayoutConstraint.activate([chip.heightAnchor.constraint(equalToConstant: 40),
            link.centerYAnchor.constraint(equalTo: chip.centerYAnchor),
            link.leadingAnchor.constraint(equalTo: chip.leadingAnchor, constant: 14), link.trailingAnchor.constraint(equalTo: chip.trailingAnchor, constant: -14)])
        caption.font = .systemFont(ofSize: 17); caption.textColor = .secondaryLabelColor; caption.alignment = .center; caption.isHidden = true
        link.font = .monospacedSystemFont(ofSize: 13, weight: .medium); link.isSelectable = true; link.alignment = .center
        link.lineBreakMode = .byTruncatingMiddle; link.isHidden = true
        for (b, primary) in [(open, true), (copy, false), (retry, true)] {
            b.isBordered = false; b.wantsLayer = true; b.layer?.cornerRadius = 15; b.isHidden = true; b.target = self
            b.layer?.backgroundColor = primary ? NSColor.controlAccentColor.cgColor : NSColor.labelColor.withAlphaComponent(0.08).cgColor
            b.heightAnchor.constraint(equalToConstant: primary ? 56 : 50).isActive = true
            setBtn(b, b.title, primary: primary)
        }
        open.keyEquivalent = "\r"; open.action = #selector(openApp); copy.action = #selector(copyLink); retry.action = #selector(retryStart)
        let stack = NSStackView(views: [title, status, spinner, detail, card, caption, chip, open, copy, retry])
        stack.orientation = .vertical; stack.alignment = .centerX; stack.spacing = 16; stack.setCustomSpacing(6, after: title); stack.setCustomSpacing(26, after: caption)
        stack.translatesAutoresizingMaskIntoConstraints = false
        let cv = win.contentView!; cv.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: cv.topAnchor, constant: 48), stack.centerXAnchor.constraint(equalTo: cv.centerXAnchor),
            stack.widthAnchor.constraint(equalToConstant: 400),
            spinner.widthAnchor.constraint(equalToConstant: 300), status.widthAnchor.constraint(equalToConstant: 400),
            detail.widthAnchor.constraint(equalToConstant: 400), caption.widthAnchor.constraint(equalToConstant: 400),
            chip.widthAnchor.constraint(equalToConstant: 380), open.widthAnchor.constraint(equalToConstant: 320),
            copy.widthAnchor.constraint(equalToConstant: 320), retry.widthAnchor.constraint(equalToConstant: 320)])
        status.stringValue = "Đang kiểm tra…"
        win.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.tick() }
        tick()
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }

    @objc func openApp() { if let b = base { NSWorkspace.shared.open(URL(string: b + "/")!) } }
    @objc func copyLink() {
        NSPasteboard.general.clearContents(); NSPasteboard.general.setString(shownURL, forType: .string)
        setBtn(copy, "Đã chép ✓", primary: false); DispatchQueue.main.asyncAfter(deadline: .now() + 2) { setBtn(self.copy, "Chép link", primary: false) }
    }
    @objc func retryStart() { started = false; startedAt = Date(); retry.isHidden = true; spinner.isHidden = false; tick() }

    func tick() {
        if busy { return }; busy = true
        DispatchQueue.global().async {
            let b = findBase()
            var items: [[String: Any]] = []
            if let b = b, let d = fetch(b + "/api/links", timeout: 3),
               let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any], let it = j["items"] as? [[String: Any]] { items = it }
            let pick = items.first { ($0["url"] as? String ?? "").hasPrefix("https") } ?? items.first
            var img: NSImage?; let url = pick?["url"] as? String ?? ""
            if let b = b, !url.isEmpty, url != self.shownURL,
               let q = url.addingPercentEncoding(withAllowedCharacters: .alphanumerics),
               let d = fetch(b + "/api/qr.png?u=" + q, timeout: 4) { img = NSImage(data: d) }
            DispatchQueue.main.async { self.busy = false; self.update(b, url, (pick?["url"] as? String ?? "").hasPrefix("https"), img) }
        }
    }

    func update(_ b: String?, _ url: String, _ isHttps: Bool, _ img: NSImage?) {
        base = b
        if b != nil {
            spinner.isHidden = true; detail.isHidden = true; retry.isHidden = true
            let ok = NSMutableAttributedString(string: "● ", attributes: [.foregroundColor: NSColor.systemGreen, .font: NSFont.systemFont(ofSize: 14)])
            ok.append(NSAttributedString(string: "ScanApp đã sẵn sàng", attributes: [.foregroundColor: NSColor.labelColor, .font: NSFont.systemFont(ofSize: 20, weight: .semibold)]))
            let ps = NSMutableParagraphStyle(); ps.alignment = .center; ok.addAttribute(.paragraphStyle, value: ps, range: NSRange(location: 0, length: ok.length))
            status.attributedStringValue = ok
            [card, qr, caption, chip, link, open, copy].forEach { $0.isHidden = false }
            if let i = img { qr.image = i }
            if !url.isEmpty { shownURL = url; link.stringValue = url }
            caption.stringValue = isHttps ? "Dùng camera điện thoại quét mã này để mở app"
                                          : "Đang tạo link https cho camera điện thoại… (vài giây)\nTạm thời quét mã này (cùng wifi)"
            return
        }
        [card, qr, caption, chip, link, open, copy].forEach { $0.isHidden = true }; shownURL = ""
        if !started { started = true; startedAt = Date(); startViaTerminal() }
        let li = logInfo()
        if let rc = li.endRC, rc != 0 || Date().timeIntervalSince(startedAt) > 20 {
            spinner.isHidden = true; retry.isHidden = false; detail.isHidden = false
            status.stringValue = "Chưa bật được ScanApp"
            detail.stringValue = "Mở cửa sổ Terminal (dưới Dock) hoặc file logs/server.log trong thư mục scan-app để xem lỗi.\n" + li.last
            return
        }
        spinner.isHidden = false; detail.isHidden = false
        status.stringValue = li.mode == "install" ? "Đang cài đặt lần đầu…\nCó thể mất vài phút, xin đừng tắt máy"
                                                  : "Đang bật ScanApp…"
        detail.stringValue = li.last
    }
}

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
