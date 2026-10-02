# Android Installation & Sideloading Guide

This guide explains how to install and configure **YOuTUbE** on your Android smartphone or tablet.

---

## 1. Prerequisites
- **Android Version:** Android 8.0 (Oreo) or higher (API 26+).
- **Storage:** ~180 MB free storage for application binaries and runtimes.
- **Package:** `YOuTUbE.apk` (Download from GitHub Releases or `Output/YOuTUbE.apk`).

---

## 2. Enabling "Install Unknown Apps"

Because Google Play Store policies do not permit YouTube media downloading applications, YOuTUbE is distributed directly as an APK.

### Android 8.0 through Android 15:
1. Download `YOuTUbE.apk` to your phone using Chrome, Firefox, or transfer it from your PC via USB cable.
2. Open your phone's **Files** or **Downloads** app and tap `YOuTUbE.apk`.
3. If prompted with *"For your security, your phone is not allowed to install unknown apps from this source"*:
   - Tap **Settings** in the popup prompt.
   - Toggle **Allow from this source** to **ON**.
   - Tap the back button to return to the installer.
4. Tap **Install** and wait for the installation to finish.
5. Tap **Open**.

---

## 3. First Launch & Permissions
On first launch, YOuTUbE will request:
- **Notifications:** Required on Android 13+ to display foreground download progress %, ETA, and the Cancel button in your notification drawer.
- **Storage / Media Access:** Used to export finished audio and video files directly into your standard device folders (`Movies/YOuTUbE/` and `Music/YOuTUbE/`).

---

## 4. Using the App

### Method A: Direct Paste
1. Copy any video link from YouTube or your web browser.
2. Open **YOuTUbE** and tap **Paste** (or paste into the URL field).
3. The video title and available resolutions are automatically fetched.
4. Tap the red **Download** button.

### Method B: Native Android Share Sheet
1. While watching any video in the official YouTube app or your browser, tap **Share**.
2. Select **YOuTUbE** from the share sheet app list.
3. YOuTUbE will open automatically, paste the link, and fetch metadata ready for 1-tap downloading.

---

## 5. Offline Operation
- When disconnected from the internet, the status dot turns red ("Offline").
- The **History** tab remains fully operational offline. You can tap any downloaded item to play it in your favorite media player (VLC, MX Player, Google Files, etc.) or re-download once back online.
