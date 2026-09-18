import SwiftUI
import WidgetKit

/// The home-screen widget: the one figure the app puts first, nothing else.
///
/// It never calls the network and never sees a session. The app writes a
/// small snapshot into the shared App Group each time it shows the Overview
/// (see TangentNativePlugin.setWidgetSnapshot); the widget reads it back and
/// displays it as is. Labels and amounts arrive already written in the
/// person's language, so the widget follows the app's own language setting
/// without repeating the translations or the number formats in Swift.
///
/// No snapshot yet (never opened, or signed out) means no figures: the widget
/// shows its name and a dash rather than a stale amount presented as current.

// MARK: - What the app hands over

struct WealthSnapshot: Codable {
    /// « Patrimoine net » / "Net worth", as the Overview writes it.
    let label: String
    /// The amount, formatted by the app: « 19 600,55 € » or "€19,600.55".
    let value: String
    /// One line under it, when there is something to say (debts, performance).
    let sub: String?
    /// Tints `sub`: true green, false red, nil neutral.
    let positive: Bool?
    let updatedAt: Date

    static let appGroup = "group.uk.riskybusinesses.tangent"
    static let key = "wealth"

    static func read() -> WealthSnapshot? {
        guard let defaults = UserDefaults(suiteName: appGroup),
              let data = defaults.data(forKey: key)
        else { return nil }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try? decoder.decode(WealthSnapshot.self, from: data)
    }
}

// MARK: - Timeline

struct WealthEntry: TimelineEntry {
    let date: Date
    let snapshot: WealthSnapshot?
}

struct WealthProvider: TimelineProvider {
    /// The gallery preview: plausible figures, never someone's own.
    func placeholder(in context: Context) -> WealthEntry {
        WealthEntry(
            date: Date(),
            snapshot: WealthSnapshot(
                label: "Patrimoine net",
                value: "19 600,55 €",
                sub: nil,
                positive: nil,
                updatedAt: Date()
            )
        )
    }

    func getSnapshot(in context: Context, completion: @escaping (WealthEntry) -> Void) {
        if context.isPreview {
            completion(placeholder(in: context))
            return
        }
        completion(WealthEntry(date: Date(), snapshot: WealthSnapshot.read()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<WealthEntry>) -> Void) {
        // One entry, kept until the app writes a new snapshot and asks for a
        // reload. The hourly refresh is only there so the « updated » line
        // does not freeze if the app is never opened.
        let entry = WealthEntry(date: Date(), snapshot: WealthSnapshot.read())
        let next = Calendar.current.date(byAdding: .hour, value: 1, to: Date()) ?? Date()
        completion(Timeline(entries: [entry], policy: .after(next)))
    }
}

// MARK: - Views

private extension View {
    /// iOS 17 asks a widget to declare its background; earlier versions paint it.
    @ViewBuilder
    func widgetBackground(_ color: Color) -> some View {
        if #available(iOS 17.0, *) {
            containerBackground(color, for: .widget)
        } else {
            background(color)
        }
    }
}

struct WealthWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: WealthEntry

    private var background: Color { Color(red: 0.039, green: 0.039, blue: 0.039) }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let snapshot = entry.snapshot {
                Text(snapshot.label.uppercased())
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
                Text(snapshot.value)
                    .font(family == .systemSmall ? .title3 : .title)
                    .fontWeight(.semibold)
                    .minimumScaleFactor(0.6)
                    .lineLimit(1)
                if let sub = snapshot.sub {
                    Text(sub)
                        .font(.caption)
                        .foregroundColor(tint(snapshot.positive))
                        .lineLimit(family == .systemSmall ? 2 : 1)
                }
                Spacer(minLength: 0)
                Text(snapshot.updatedAt, style: .relative)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            } else {
                Text("Tangent")
                    .font(.headline)
                Text("—")
                    .font(.title)
                    .foregroundColor(.secondary)
                Spacer(minLength: 0)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(family == .systemSmall ? 12 : 16)
        .widgetBackground(background)
        .widgetURL(URL(string: "tangent://open"))
    }

    private func tint(_ positive: Bool?) -> Color {
        switch positive {
        case .some(true): return Color(red: 0.13, green: 0.77, blue: 0.51)
        case .some(false): return Color(red: 0.94, green: 0.33, blue: 0.31)
        case .none: return .secondary
        }
    }
}

// MARK: - Widget

struct WealthWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "TangentWealth", provider: WealthProvider()) { entry in
            WealthWidgetView(entry: entry)
        }
        .configurationDisplayName("Tangent")
        .description("Ton patrimoine, d'un coup d'œil.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

@main
struct TangentWidgetBundle: WidgetBundle {
    var body: some Widget {
        WealthWidget()
    }
}
