import AuthenticationServices
import Capacitor
import CryptoKit
import Foundation
import LocalAuthentication

/// What the web code cannot do by itself on the phone (ADR-035):
/// unlock with Face ID, run an OAuth round trip in the system's secure
/// browser, and Sign in with Apple through iOS. Registered by
/// `TangentViewController`; typed on the JS side in src/native/bridge.ts.
@objc(TangentNativePlugin)
public class TangentNativePlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "TangentNativePlugin"
    public let jsName = "TangentNative"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "unlock", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "authSession", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "appleSignIn", returnType: CAPPluginReturnPromise),
    ]

    private var webSession: ASWebAuthenticationSession?
    private var appleFlow: AppleSignInFlow?

    // MARK: Face ID / Touch ID, device passcode as fallback

    @objc func unlock(_ call: CAPPluginCall) {
        let context = LAContext()
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error) else {
            // No biometrics and no passcode on this phone: nothing to ask, let the person in.
            call.resolve(["available": false, "success": true])
            return
        }
        let reason = call.getString("reason") ?? "Déverrouiller Tangent"
        context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reason) { ok, _ in
            call.resolve(["available": true, "success": ok])
        }
    }

    // MARK: OAuth in the system browser (Google, Apple on the web, the banks)

    @objc func authSession(_ call: CAPPluginCall) {
        guard let urlString = call.getString("url"), let url = URL(string: urlString) else {
            call.reject("url manquante")
            return
        }
        let scheme = call.getString("callbackScheme") ?? "tangent"
        DispatchQueue.main.async {
            let session = ASWebAuthenticationSession(url: url, callbackURLScheme: scheme) { [weak self] callbackURL, error in
                self?.webSession = nil
                if let callbackURL = callbackURL {
                    call.resolve(["url": callbackURL.absoluteString])
                } else {
                    call.reject(error?.localizedDescription ?? "Connexion annulée.", "cancelled")
                }
            }
            session.presentationContextProvider = self
            // Shares Safari's cookies: someone already signed in to Google there is not asked twice.
            session.prefersEphemeralWebBrowserSession = false
            self.webSession = session
            if !session.start() {
                self.webSession = nil
                call.reject("Le navigateur système n'a pas pu s'ouvrir.")
            }
        }
    }

    // MARK: Sign in with Apple, natively

    @objc func appleSignIn(_ call: CAPPluginCall) {
        // The JS side sends the SHA-256 (hex) of a random nonce and posts the same
        // value to the backend, which compares it with the id_token's nonce claim.
        let hashedNonce = call.getString("nonce") ?? ""
        DispatchQueue.main.async {
            let request = ASAuthorizationAppleIDProvider().createRequest()
            request.requestedScopes = [.fullName, .email]
            if !hashedNonce.isEmpty {
                request.nonce = hashedNonce
            }
            let flow = AppleSignInFlow(call: call, anchor: self.anchor()) { [weak self] in
                self?.appleFlow = nil
            }
            self.appleFlow = flow
            let controller = ASAuthorizationController(authorizationRequests: [request])
            controller.delegate = flow
            controller.presentationContextProvider = flow
            controller.performRequests()
        }
    }

    private func anchor() -> ASPresentationAnchor {
        return bridge?.viewController?.view.window ?? ASPresentationAnchor()
    }
}

extension TangentNativePlugin: ASWebAuthenticationPresentationContextProviding {
    public func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        return anchor()
    }
}

/// One Sign in with Apple attempt: holds the call until iOS answers.
final class AppleSignInFlow: NSObject, ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding {
    private let call: CAPPluginCall
    private let anchor: ASPresentationAnchor
    private let done: () -> Void

    init(call: CAPPluginCall, anchor: ASPresentationAnchor, done: @escaping () -> Void) {
        self.call = call
        self.anchor = anchor
        self.done = done
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        defer { done() }
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
              let data = credential.identityToken,
              let token = String(data: data, encoding: .utf8) else {
            call.reject("Apple n'a pas renvoyé de jeton.")
            return
        }
        var result: [String: Any] = ["identityToken": token]
        if let email = credential.email { result["email"] = email }
        if let name = credential.fullName?.givenName { result["givenName"] = name }
        call.resolve(result)
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithError error: Error) {
        defer { done() }
        call.reject(error.localizedDescription, "cancelled")
    }

    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        return anchor
    }
}
