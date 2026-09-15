import Capacitor
import UIKit

/// The bridge with Tangent's own plugin on board.
class TangentViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        bridge?.registerPluginInstance(TangentNativePlugin())
    }
}
