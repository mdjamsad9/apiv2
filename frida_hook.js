// Frida hook for Crexify TV - intercepts AES decryption
// Hooks:
//   1. com.bumptech.glide.d.e(String) - SetA AES-CBC decrypt
//   2. e3.b decryption logic (SetB AES-CBC decrypt)
//   3. javax.crypto.Cipher.doFinal (catches all AES decrypt calls)

Java.perform(function () {
    console.log("[*] Frida hook loaded - Crexify TV decryption interceptor");
    console.log("[*] Hooking javax.crypto.Cipher.doFinal...");

    var Cipher = Java.use("javax.crypto.Cipher");
    var String = Java.use("java.lang.String");

    // Hook doFinal(byte[]) - single-part decryption
    Cipher.doFinal.overload('[B').implementation = function (input) {
        try {
            var result = this.doFinal(input);
            var algorithm = this.getAlgorithm();
            if (algorithm.indexOf("AES") !== -1) {
                // Only log decrypt operations (opmode == 2)
                try {
                    var resultStr = String.$new(result);
                    var preview = resultStr.substring(0, Math.min(500, resultStr.length()));
                    if (preview.startsWith("[") || preview.startsWith("{")) {
                        console.log("\n[+] AES Decryption RESULT (JSON detected!):");
                        console.log("    Algorithm: " + algorithm);
                        console.log("    Input len: " + input.length);
                        console.log("    Output: " + preview);
                    }
                } catch (e) {
                    // Not a valid string - skip
                }
            }
            return result;
        } catch (e) {
            console.log("[-] Cipher.doFinal error: " + e);
            throw e;
        }
    };

    // Hook com.bumptech.glide.d.e(String str) - the Set A decrypt method
    try {
        var dClass = Java.use("com.bumptech.glide.d");
        dClass.e.overload("java.lang.String").implementation = function (str) {
            console.log("\n[*] com.bumptech.glide.d.e() called");
            console.log("    Input (first 100): " + str.substring(0, Math.min(100, str.length())));
            var result = this.e(str);
            console.log("    Output (first 500): " + result.substring(0, Math.min(500, result.length())));
            return result;
        };
        console.log("[+] Hooked com.bumptech.glide.d.e(String)");
    } catch (e) {
        console.log("[-] Failed to hook com.bumptech.glide.d.e: " + e);
    }

    // Hook e3.b network callback to catch response body before decryption
    try {
        var e3b = Java.use("e3.b");
        // Find and hook the method that processes network response
        // Based on source code analysis: method k() processes the response string
        var methods = e3b.class.getDeclaredMethods();
        methods.forEach(function (m) {
            var name = m.getName();
            var params = m.getParameterTypes();
            if (params.length === 1 && params[0].getName() === "java.lang.String") {
                console.log("[*] e3.b method found: " + name + "(String)");
            }
        });
    } catch (e) {
        console.log("[-] Failed to inspect e3.b: " + e);
    }

    // Hook SecretKeySpec to capture AES keys being used
    try {
        var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
        SecretKeySpec.$init.overload('[B', 'java.lang.String').implementation = function (keyBytes, algorithm) {
            if (algorithm === "AES") {
                var keyStr = "";
                for (var i = 0; i < keyBytes.length; i++) {
                    keyStr += String.fromCharCode(keyBytes[i] & 0xFF);
                }
                console.log("\n[*] AES SecretKeySpec created with key: " + keyStr);
            }
            return this.$init(keyBytes, algorithm);
        };
        console.log("[+] Hooked SecretKeySpec.$init");
    } catch (e) {
        console.log("[-] Failed to hook SecretKeySpec: " + e);
    }

    // Hook IvParameterSpec to capture IVs
    try {
        var IvParameterSpec = Java.use("javax.crypto.spec.IvParameterSpec");
        IvParameterSpec.$init.overload('[B').implementation = function (ivBytes) {
            var ivStr = "";
            for (var i = 0; i < ivBytes.length; i++) {
                ivStr += String.fromCharCode(ivBytes[i] & 0xFF);
            }
            console.log("[*] IvParameterSpec created with IV: " + ivStr);
            return this.$init(ivBytes);
        };
        console.log("[+] Hooked IvParameterSpec.$init");
    } catch (e) {
        console.log("[-] Failed to hook IvParameterSpec: " + e);
    }

    // Hook Base64 decode to see what gets decoded
    try {
        var Base64 = Java.use("android.util.Base64");
        Base64.decode.overload('java.lang.String', 'int').implementation = function (str, flags) {
            var result = this.decode(str, flags);
            if (str.length() > 50) {
                console.log("\n[*] Base64.decode(String) called:");
                console.log("    Input (first 80): " + str.substring(0, Math.min(80, str.length())));
                console.log("    Output length: " + result.length);
            }
            return result;
        };
        console.log("[+] Hooked Base64.decode(String, int)");
    } catch (e) {
        console.log("[-] Failed to hook Base64.decode: " + e);
    }

    console.log("\n[*] All hooks installed. Waiting for decryption calls...\n");
});
