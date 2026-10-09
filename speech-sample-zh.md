# Speech-to-text sample: Chinese

- Machine: macOS-26.6.2-arm64-arm-64bit, arm64, processor only

## Kokoro Mandarin (zf_xiaobei), known text

Reference: 蜂蜜永远不会变质。考古学家在埃及古墓中发现了三千年前的蜂蜜，至今仍然可以食用。章鱼有三颗心脏，其中两颗在它游泳的时候会停止跳动。金星上的一天比它的一年还要长。竹子是世界上生长最快的植物之一，有些品种一天可以长近一米。这种水母可以长生不老。它受伤以后，会变回水螅，重新开始生命。那么接下来会发生什么呢？我们一起去看看吧。

| Engine | Text | Simplified CER | Speed (x real time) | Timings | First timings |
| --- | --- | --- | --- | --- | --- |
| SenseVoice-Small int8 (sherpa-onnx) | 蜂蜜永远不会变质考古学家在埃及古墓中发现了三千年前的蜂蜜至今仍然可以食用章鱼有三颗心脏其中两颗在它游泳的时候会停止跳动金星上的一天比它的一年还要长竹子是世界上生长最快的植物之一有些品种一天可以长进一米这种水母可以长生不老它受伤以后会变回水溪重新开始生命那么接下来会发生什么呢我们一起去看看吧 | 1.4% | 11.4x | 145 token times | [["蜂", 0.12], ["蜜", 0.3], ["永", 0.6], ["远", 0.78], ["不", 0.96], ["会", 1.14]] |
| Whisper small int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |
| Whisper large-v3-turbo int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |

## SenseVoice test recording zh.wav (human)

| Engine | Text | Simplified CER | Speed (x real time) | Timings | First timings |
| --- | --- | --- | --- | --- | --- |
| SenseVoice-Small int8 (sherpa-onnx) | 饭时间早上九点至下午五点 | - | 10.2x | 12 token times | [["饭", 0.9], ["时", 1.26], ["间", 1.5], ["早", 1.86], ["上", 2.1], ["九", 2.52]] |
| Whisper small int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |
| Whisper large-v3-turbo int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |

## SenseVoice test recording yue.wav (human)

| Engine | Text | Simplified CER | Speed (x real time) | Timings | First timings |
| --- | --- | --- | --- | --- | --- |
| SenseVoice-Small int8 (sherpa-onnx) | 呢几个字都表达唔到我想讲嘅意思 | - | 9.7x | 15 token times | [["呢", 0.78], ["几", 1.08], ["个", 1.26], ["字", 1.44], ["都", 1.68], ["表", 1.98]] |
| Whisper small int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |
| Whisper large-v3-turbo int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |

## SenseVoice test recording en.wav (human)

| Engine | Text | Simplified CER | Speed (x real time) | Timings | First timings |
| --- | --- | --- | --- | --- | --- |
| SenseVoice-Small int8 (sherpa-onnx) | THE TRIVBAL CHIEF THIN CALLED FOR THE BOY AND PRESENTED HIM WITH FIFTY PIECES OF COOD | - | 10.2x | 66 token times | [["T", 0.84], ["H", 0.9], ["E", 1.02], [" T", 1.14], ["R", 1.2], ["I", 1.26]] |
| Whisper small int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |
| Whisper large-v3-turbo int8 (faster-whisper) | failed: TypeError: open() got an unexpected keyword argument 'metadata_errors' | | | | |

