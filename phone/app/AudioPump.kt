package io.callpilot.phone

/**
 * Stub only. There is no Gradle project and this file is not a buildable app.
 * Wire-up steps live in phone/README.md.
 *
 * The laptop decoder in laptop/stt/pcm.py is the contract for each frame:
 * uint32be header length, UTF-8 JSON header, uint32be pcm length, pcm bytes.
 * Push that stream to 127.0.0.1:8770 and let the laptop `adb forward` it.
 * Do not put Gladia or Holo keys on the phone.
 */
interface AudioPump {
    fun start(callId: String)
    fun stop()
}
