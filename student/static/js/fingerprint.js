// student/static/js/fingerprint.js
export async function enableFingerprint(username, buttonId, statusId) {
    const statusEl = document.getElementById(statusId);
    statusEl.className = "status-waiting";
    statusEl.innerText = "Generating registration options...";

    try {
        console.log("Fetching registration options for user:", username);
        const optionsResp = await fetch(`/webauthn/register/options?username=${username}`);
        if (!optionsResp.ok) throw new Error(`Failed to get options: ${optionsResp.statusText}`);
        const options = await optionsResp.json();
        console.log("Registration options received:", options);

        // Convert challenge & user.id to ArrayBuffer
        options.challenge = Uint8Array.from(atob(options.challenge), c => c.charCodeAt(0));
        options.user.id = Uint8Array.from(atob(options.user.id), c => c.charCodeAt(0));

        statusEl.innerText = "Prompting for biometric authentication...";
        console.log("Calling navigator.credentials.create...");

        const credential = await navigator.credentials.create({ publicKey: options });
        console.log("Credential created:", credential);

        // Convert ArrayBuffers to base64
        function arrayBufferToBase64(buffer) {
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        }

        const credentialData = {
            id: credential.id,
            rawId: arrayBufferToBase64(credential.rawId),
            type: credential.type,
            response: {
                clientDataJSON: arrayBufferToBase64(credential.response.clientDataJSON),
                attestationObject: arrayBufferToBase64(credential.response.attestationObject)
            },
            username: username
        };

        statusEl.innerText = "Verifying credential...";
        console.log("Sending credential to server for verification");

        const verifyResp = await fetch("/webauthn/register/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(credentialData)
        });

        const verifyResult = await verifyResp.json();
        console.log("Server verification result:", verifyResult);

        if (verifyResp.ok && verifyResult.status === "Fingerprint registered!") {
            statusEl.className = "status-success";
            statusEl.innerText = "✔ Fingerprint registration successful!";
            alert("Fingerprint registered successfully!");
        } else {
            statusEl.className = "status-error";
            statusEl.innerText = `❌ Error: ${verifyResult.message || "Unknown error"}`;
        }

    } catch (err) {
        console.error("Error during fingerprint registration:", err);
        statusEl.className = "status-error";
        statusEl.innerText = `❌ Error: ${err.message}`;
        alert(`Error: ${err.message}`);
    }
}
