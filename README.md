[阅读中文文档 (Read Chinese Document)](src/README-CN.md)

# AI Video Understanding Tool

## 1. Project Background

The public domain (such as video websites, live streaming platforms) contains massive amounts of game video content, holding rich information about player behavior, game trends, and community hotspots. However, the industry currently lacks large video models capable of direct, efficient end-to-end deep understanding. To address this challenge, this project explores a strategy combining multi-modal information and Large Language Models (LLMs) to achieve automated analysis and summarization of game video content.

By analyzing the **speech content** (transcribed via ASR) and **visual text information** (extracting subtitles or recognized relevant text from the screen) in the video, combined with the reasoning and summarization capabilities of LLMs, the aim is to quickly grasp the core of the video, providing technical support for scenarios like content analysis and trend mining. This approach aims to compensate for the current shortcomings in video understanding capabilities and provide a practical solution.

## 2. Project Module Introduction

This project mainly consists of the following core modules:

*   `src/video_processor.py`: Responsible for the underlying video processing, using FFmpeg to extract video frames and audio streams.
*   `src/audio_transcriber.py`: Calls the OpenAI Whisper model to transcribe the extracted audio into text and generate segmented information with timestamps. Saves in both `.json` and `.txt` formats.
*   `src/visual_extractor.py`: The core visual analysis module, responsible for:
    *   Calling AI services (like Qwen-VL) to analyze video frames and extract text (potential subtitles) from images.
    *   Implementing intelligent frame selection strategies, combined with audio transcription results, to optimize analysis efficiency.
    *   Utilizing multi-threading to parallelize the AI analysis tasks for selected frames, improving processing speed.
    *   Post-processing the extracted raw subtitles (deduplication, merging).
*   `src/ai_service.py`: Encapsulates calls to third-party AI model APIs, currently integrating Qwen and Google Gemini. Qwen is used for image description (subtitle extraction) and text generation (summarization), while Gemini is primarily used for text generation (summarization). The service prioritizes Gemini for summarization based on API key configuration, falling back to Qwen if Gemini is unavailable.
*   `src/summarizer.py`: Uses `AIService` to generate the final video content summary based on the provided text (speech transcription, subtitles, video description). Which AI model (Gemini or Qwen) is used depends on the configuration and availability in `AIService`.
*   `src/subtitle_processor.py`: Deduplicates, merges, and formats the raw subtitle results extracted by `visual_extractor`, generating standard subtitle files (like SRT).
*   `src/config.py`: Global configuration module, managing API keys, paths, processing thresholds, thread counts, etc.
*   `src/main.py`: The main project entry point, coordinating various modules to complete the entire video processing workflow and providing a command-line interface.

## 3. Module Workflow

The tool is driven by the `src/main.py` script, executing the following main steps:

1.  **Clean Output Directory**: Deletes old files in the specified output directory (defaults to `output/`) to ensure a clean run each time.
2.  **Parse Arguments**: Receives command-line input for the video path, output directory, frame extraction rate, and an optional video description.
3.  **Set Environment & Configuration**:
    *   If a video description is provided via command line, sets it to the `VIDEO_DESCRIPTION` environment variable.
    *   Loads environment variables from the `.env` file (like API keys).
    *   Dynamically sets output file paths in the `config` module based on the video filename and output directory.
4.  **Initialize Modules**: Creates instances of core classes like `VideoProcessor`, `AudioTranscriber`, `VisualExtractor`, `Summarizer`, `AIService`, etc.
5.  **Step 1: Extract Video Frames** (`VideoProcessor`): Extracts frame images from the video based on the specified frame rate (`--frame-rate`), saving them to `output/frames/<video_name>/`.
6.  **Step 2: Extract Audio** (`VideoProcessor`): Extracts the audio stream from the video, saving it as a WAV file (suitable for Whisper) to `audio/<video_name>.wav`.
7.  **Step 3: Transcribe Audio** (`AudioTranscriber`): Calls the Whisper model to process the extracted audio, generating transcription results. Saves simultaneously in JSON format (including timestamps, path specified by `config.TRANSCRIPT_PATH`) and TXT format (comma-separated text).
8.  **Step 4: Extract Video Subtitles** (`VisualExtractor.analyze_batch`):
    *   Intelligently selects key frames for analysis based on audio transcription timestamp information and configured sampling intervals.
    *   Uses multi-threading to parallelly call the AI service to analyze selected frames and extract raw text information.
    *   Post-processes the raw results (`SubtitleProcessor`), merging similar subtitles, removing invalid content, and generating the final processed subtitle list.
    *   Saves the processed subtitles in JSON format (`config.SUBTITLES_JSON_PATH`) and SRT format (`config.SUBTITLES_SRT_PATH`), and saves the concatenated plain text (`config.SUBTITLES_RESULT_PATH`).
9.  **Step 5: Collect Valid Subtitles** (`collect_subtitles`): Extracts the list of valid subtitle texts from the processed results of the previous step. If the previous step failed to extract successfully (e.g., API call failure), attempts to load from the saved subtitle JSON file.
10. **Step 6: Prepare Summary Input** (`prepare_summary_input`):
    *   Loads the TXT format speech transcription text generated in Step 3.
    *   Checks if the subtitle list collected in Step 5 is valid (non-empty and total length meets the `config.MIN_VALID_SUBTITLE_LENGTH` threshold).
    *   If subtitles are valid, merges the speech transcription and subtitle content.
    *   If subtitles are invalid, checks `config.VIDEO_DESCRIPTION` (from environment variable or command-line argument). If it exists, merges the speech transcription and video description; otherwise, uses only the speech transcription.
11. **Step 7: Generate Summary** (`Summarizer` -> `AIService`):
    *   Checks if the input text prepared in Step 6 is long enough (meets the `config.MIN_SUMMARY_INPUT_LENGTH` threshold).
    *   If the text is long enough, calls `AIService` via `Summarizer` to generate a content summary. `AIService` will first try to use Gemini if the Gemini API key is configured and available; otherwise, it falls back to using the Qwen model.
    *   If the text is too short or empty, skips summary generation.
12. **Save Summary**: Saves the generated summary (or an informational message) to the file specified by `config.SUMMARY_OUTPUT_PATH`.
13. **Completion**: Outputs a completion message.

## 4. Project Configuration and Usage Introduction

### 4.1 Configuration

Main configurations are managed through `src/config.py` and the `.env` file in the project root directory.

*   **.env.example File**: The project root provides a `.env.example` file as a template. It lists all required and optional environment variables (mainly API keys).
*   **.env File** (Needs to be manually created based on `.env.example`):
    *   **Important**: Copy `.env.example` and rename the copy to `.env`.
    *   Open the `.env` file and replace the example values (like `sk-your_qwen_api_key_here`) with your **actual API keys**.
    *   Uncomment and set optional variables as needed (like `VIDEO_DESCRIPTION`, `GEMINI_BASE_URL`).
    *   The `.env` file is used to store sensitive information and will be loaded automatically by the program.
    *   **Security Tip**: The `.env` file usually contains sensitive credentials. **Never** commit it to version control systems like Git. The `.gitignore` file should include `.env` to prevent accidental commits.
    *   Example `.env` file content (after filling):
        ```dotenv
        # .env (Example after filling)
        QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
        GEMINI_API_KEY=AIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # GEMINI_BASE_URL=https://my-proxy.com/
        ```
*   **src/config.py File**:
    *   Defines the output directory structure (`OUTPUT_DIR`, `FRAMES_DIR`, etc.).
    *   Defines dynamic path variables (like `TRANSCRIPT_PATH`, `SUBTITLES_JSON_PATH`, etc.), which are dynamically filled in `main.py` based on the video name.
    *   Defines processing thresholds:
        *   `SUBTITLE_MERGE_THRESHOLD_SIMILARITY`: Similarity threshold for merging subtitles.
        *   `SUBTITLE_MERGE_THRESHOLD_TIME`: Time interval threshold for merging subtitles.
        *   `MIN_VALID_SUBTITLE_LENGTH`: Minimum total length to consider extracted subtitles valid.
    *   Defines multi-threading configuration:
        *   `VISUAL_EXTRACTION_MAX_WORKERS`: Maximum number of threads used during subtitle extraction.
    *   Reads `VIDEO_DESCRIPTION` from the environment variable.

### 4.2 Usage

Run the `src/main.py` script via the command line to start the video processing workflow.

**Basic Usage:**

```bash
python -m src.main <video_path> [options]
```

**Argument Description:**

*   `video_path` (Required): The full path to the video file to be processed.
*   `--output` or `-o` (Optional): Specifies the root directory for output files, defaults to `output`.
*   `--frame-rate` (Optional): Specifies the number of video frames to extract per second, defaults to `5`. A higher frame rate extracts more frames, potentially improving subtitle recognition accuracy but increasing processing time.
*   `--description` or `-d` (Optional): Provides a description of the video. If no valid subtitles are extracted, this description will be used along with the speech transcription to generate the summary.

**Examples:**

```bash
# Process video using default output directory and frame rate
python -m src.main "/path/to/my_video.mp4"

# Specify output directory and frame rate, and provide a video description
python -m src.main "/path/to/another_video.avi" -o "results" --frame-rate 2 -d "This is a demo video about scenery"
```

After processing is complete, all intermediate files (frames, audio, transcription, subtitles) and the final summary file (`final_summary.txt`) will be saved in the specified output directory.

## 5. Technical Optimization Details and Principles for Subtitle Extraction Speed

Video subtitle extraction (`VisualExtractor.analyze_batch`) is a relatively time-consuming part of the project, with the main bottleneck being the AI service API calls required for image analysis of each frame (network I/O intensive). To improve processing speed, I have adopted the following **three** key technical optimizations:

### 5.1 Video Frame Extraction Sampling Rate Optimization (FPS)

This is the first optimization step in the processing flow. Using the command-line argument `--frame-rate` (or `-fps`), the user can control the frequency (frames extracted per second) at which frame images are decoded and extracted from the original video.

*   **Principle**: Videos often contain many redundant frames, especially in slowly changing scenes or static shots. Not every frame needs to be extracted for subsequent analysis. By setting a reasonable sampling rate (e.g., 1, 2, or 5 frames per second), the number of initial frames to be stored and processed can be significantly reduced.
*   **Trade-off**:
    *   **Lower FPS** (e.g., 1 or 2): Significantly reduces the number of extracted frames, speeds up video decoding, reduces disk usage, and potentially reduces the total number of frames considered by the subsequent intelligent frame selection, thus speeding up the overall process. However, **it might miss very short-duration subtitles** (e.g., subtitles flashing for only one or two frames).
    *   **Higher FPS** (e.g., 5 or more): Extracts more frames, increasing the likelihood of capturing fast-flashing subtitles. But it increases video decoding time and disk space usage, and may present a larger base for subsequent intelligent frame selection and analysis.
*   **Selection Recommendation**: The optimal FPS depends on the characteristics of the video content.
    *   For **dialogue-intensive, fast-changing subtitle** videos (like fast-paced game commentary, rapidly edited vlogs), a slightly higher FPS (e.g., 3-5) might be needed to capture all subtitles.
    *   For **slower-paced, long-duration subtitle** videos (like lectures, tutorials, scenic films), a lower FPS (e.g., 1-2) is often sufficient and significantly improves efficiency.
*   **Importance**: This is a **pre-optimization** step that determines the size of the total frame pool entering the subsequent "intelligent frame selection" stage. A reasonable FPS setting is the foundation for overall efficiency.

### 5.2 Intelligent Frame Selection Strategy

Even with a lower FPS, the extracted frame sequence may still contain many visually similar or subtitle-free frames. Intelligent frame selection aims to further skip these redundant frames, reducing unnecessary AI analysis calls.

Its principle is based on **time-driven sampling combined with audio transcription information**:

1.  **Utilize Speech Activity Detection**: First, load the timestamped speech segment information generated by `AudioTranscriber`.
2.  **Analyze Boundary Frames**: When the video transitions from a silent segment to a speech segment, or vice versa, frames at these time points often contain state changes and are more likely to have new subtitles appear. Therefore, these **boundary frames** are prioritized for analysis.
3.  **Silent Segment Sampling**: During silent periods with no speech activity, assume subtitle change frequency is low, and sample for analysis at a longer time interval (`silent_sample_interval`, e.g., 1 second).
4.  **Speech Segment Sampling**: During periods with speech activity, a sampling interval can be configured (`segment_sample_interval`, e.g., 2 seconds). If the time interval between two analyzed frames exceeds this threshold, analysis is performed. This captures potential subtitle changes during continuous dialogue. If this interval is set to 0 or negative, only the boundary frames of the speech segment are analyzed.
5.  **Always Analyze First Frame**: Ensure at least the first frame of the video is analyzed.

This strategy effectively filters out a large number of content-repetitive or subtitle-free frames, concentrating computational resources on the key frames most likely to contain information.

### 5.3 Multi-threading Parallel Processing

After the first two optimization steps, a certain number of key frames may still need analysis. Since AI calls are network I/O-intensive operations, sequential calls by a single thread would be very slow. I use multi-threading to parallelize this process.

The principle is as follows:

1.  **Task Decomposition**: `VisualExtractor` first uses the intelligent frame selection logic to sequentially determine all frames that **need** to be analyzed, collecting their paths and frame numbers into a list.
2.  **Thread Pool Execution**: A thread pool is created using Python's `concurrent.futures.ThreadPoolExecutor`, with the number of threads controlled by `config.VISUAL_EXTRACTION_MAX_WORKERS`.
3.  **Parallel API Calls**: Each frame in the list of frames to be analyzed is submitted as an independent task to the thread pool. Multiple worker threads simultaneously initiate image analysis requests to the AI service.
4.  **I/O Wait Overlapping**: When one thread is waiting for an API response (network transfer and AI processing time), other threads can continue sending requests or processing other tasks, effectively utilizing the waiting time and increasing overall throughput.
5.  **Result Collection and Sorting**: After all threads complete, the main thread collects all analysis results. Since tasks complete in parallel, the result order is scrambled. Using the previously recorded frame numbers, the results are **re-sorted** to ensure subsequent subtitle processing (like `SubtitleProcessor`) can proceed in the correct time order.

By combining **frame extraction sampling rate optimization**, **intelligent frame selection**, and **multi-threading parallel processing**, the total time required for video understanding can be significantly reduced while maintaining analysis quality (minimizing missed important subtitles).

## 6. Testing and Stability Assurance

To ensure the functional correctness of each module and the stability of the code, this project employs unit testing methods.

*   **Testing Framework**: Uses Python's built-in `unittest` framework.
*   **Test File Location**: All test case code resides in the `tests/` directory in the project root, following the `test_*.py` naming convention.
*   **Coverage**: I strive to write unit tests for the key functionalities of core modules, including:
    *   `VideoProcessor`: Testing video frame and audio extraction functions.
    *   `AudioTranscriber`: Testing Whisper model loading and audio transcription logic (may require mocking API calls or using small test audio).
    *   `VisualExtractor`: Testing intelligent frame selection logic and (by mocking the AI service) the subtitle extraction process.
    *   `AIService`: Testing API client initialization and (by mocking API calls) basic request formatting.
    *   `SubtitleProcessor`: Testing subtitle deduplication, merging, and formatting logic.
    *   Other helper functions or classes.
*   **Running Tests**: All test cases can be run using the following command:
    ```bash
    python -m unittest discover tests
    ```
    This command automatically discovers and executes all test cases in the `tests/` directory.
*   **Running a Single Test File**: If you only want to run tests for a specific module, you can specify the file path:
    ```bash
    python -m unittest tests/test_video_processor.py
    ```

Regularly running and maintaining test cases is an important part of ensuring project code quality and stability.
