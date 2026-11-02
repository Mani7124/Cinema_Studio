# 🎬 Cinema Studio

Cinema Studio is a professional desktop application engineered to generate high-fidelity, 8-second cinematic animations from static reference images using **Google Cloud Vertex AI (Veo 3.1)**. 

Built as a capstone internship project, this software abstracts heavy cloud-rendering tasks into a highly responsive, modern user interface.

## 🚀 Key Features
* **Asynchronous Architecture:** Utilizes PyQt6 `QThread` to handle Long-Running Operations (LROs) via 10-second polling loops, ensuring zero UI freezing during cloud generation.
* **Enterprise AI Integration:** Authenticates securely using Google Cloud Application Default Credentials (ADC) rather than consumer API keys.
* **Native Media Playback:** Integrated `QtMultimedia` QMediaPlayer allows users to view, scrub, and manage generated MP4 videos natively within the application.
* **Dynamic Payload Management:** Securely reads image assets as raw binary bytes and dynamically resolves MIME types to prevent API rejection.

## 🛠️ Technology Stack
* **Language:** Python 3
* **GUI Framework:** PyQt6, QtMultimedia
* **Cloud AI:** Google Cloud SDK (`google-genai`), Vertex AI (`veo-3.1-lite-generate-001`)

*Developed as part of the Batch 3 Internship at Robocoupler Pvt Ltd.*
