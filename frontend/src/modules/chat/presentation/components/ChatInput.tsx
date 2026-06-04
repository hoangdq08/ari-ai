"use client";

import { Send, Image as ImageIcon, Mic, Camera as CameraIcon, ImagePlus } from "lucide-react";
import { useRef, useState, useEffect } from "react";
import { useChat } from "../hooks/useChat";
import { useDiagnoseImage } from "@/modules/diagnostics/presentation/hooks/useDiagnoseImage";

export function ChatInput() {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [showImageMenu, setShowImageMenu] = useState(false);
  const [showVoiceTooltip, setShowVoiceTooltip] = useState(false);

  const galleryInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const recognitionRef = useRef<any>(null);
  const startXRef = useRef<number | null>(null);

  const { submitMessage, setTyping, addMessage, isTyping } = useChat();
  const diagnoseMutation = useDiagnoseImage();
  const trimmedText = text.trim();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const searchParams = new URLSearchParams(window.location.search);
      const mode = searchParams.get("mode");
      if (mode === "camera") {
        setTimeout(() => setShowImageMenu(true), 300);
      } else if (mode === "voice") {
        setTimeout(() => {
          setShowVoiceTooltip(true);
          setTimeout(() => setShowVoiceTooltip(false), 5000);
        }, 300);
      }
    }
  }, []);

  const handleSendText = (customText?: string) => {
    const textToSend = (customText ?? text).trim();
    if (!textToSend || isTyping) return;

    if (!customText) setText("");

    // Gọi lên Backend thông qua UseCase
    submitMessage(textToSend);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setShowImageMenu(false);
    if (!file) return;

    const imageUrl = URL.createObjectURL(file);

    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: "",
      imageUrl: imageUrl,
    });

    setTyping(true);
    diagnoseMutation.mutate(file, {
      onSuccess: (result) => {
        setTyping(false);
        addMessage({
          id: Date.now().toString(),
          role: "ai",
          content: result.advice,
          citation: result.citation,
        });
      },
      onError: () => {
        setTyping(false);
        addMessage({
          id: Date.now().toString(),
          role: "ai",
          content: "Xin lỗi bà con, hệ thống đang gặp lỗi. Vui lòng thử lại sau.",
        });
      }
    });

    if (galleryInputRef.current) galleryInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  };

  const handleStartRecording = (e: React.PointerEvent) => {
    e.preventDefault();
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch (err) { }
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      addMessage({
        id: Date.now().toString(),
        role: "ai",
        content: "Trình duyệt hiện chưa hỗ trợ nhận diện giọng nói. Bà con vui lòng gõ câu hỏi vào ô chat nhé.",
      });
      return;
    }

    setShowVoiceTooltip(false);
    setIsRecording(true);
    setRecordingTime(0);
    startXRef.current = e.clientX;
    recordingTimerRef.current = setInterval(() => {
      setRecordingTime((prev) => prev + 1);
    }, 1000);

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = "vi-VN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event: any) => {
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      if (transcript.trim()) {
        handleSendText(transcript);
      }
    };
    recognition.onerror = () => {
      addMessage({
        id: Date.now().toString(),
        role: "ai",
        content: "Mình chưa nghe rõ câu hỏi. Bà con thử nói lại gần micro hơn hoặc gõ trực tiếp nhé.",
      });
    };
    recognition.onend = () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      setIsRecording(false);
      setRecordingTime(0);
      recognitionRef.current = null;
    };
    recognition.start();
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isRecording || startXRef.current === null) return;
    const deltaX = startXRef.current - e.clientX;
    // Slide left > 50px to cancel
    if (deltaX > 50) {
      handleCancelRecording();
    }
  };

  const handleStopRecording = (e?: React.PointerEvent) => {
    e?.preventDefault();
    try {
      if (e) (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch (err) { }
    startXRef.current = null;
    if (!isRecording) return;

    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    setIsRecording(false);

    recognitionRef.current?.stop();
  };

  const handleCancelRecording = (e?: React.PointerEvent) => {
    e?.preventDefault();
    try {
      if (e) (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch (err) { }
    startXRef.current = null;
    if (!isRecording) return;

    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    setIsRecording(false);
    setRecordingTime(0);
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <>
      {showImageMenu && (
        <div className="fixed inset-0 z-40 pointer-events-auto bg-transparent" onClick={() => setShowImageMenu(false)}></div>
      )}

      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-[448px] px-4 z-40 pointer-events-none safe-area-pb">
        {showImageMenu && (
          <div className="absolute bottom-[80px] left-4 bg-white rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.1)] border border-slate-100 p-2 z-50 w-[200px] pointer-events-auto flex flex-col gap-1 origin-bottom-left animate-in zoom-in-95 duration-200">
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="flex items-center gap-3 px-3 py-3 w-full hover:bg-slate-50 active:bg-slate-100 rounded-xl transition-colors text-slate-700 font-medium text-[15px]"
            >
              <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center">
                <CameraIcon className="w-4 h-4 text-blue-500" />
              </div>
              <span>Chụp ảnh mới</span>
            </button>
            <button
              onClick={() => galleryInputRef.current?.click()}
              className="flex items-center gap-3 px-3 py-3 w-full hover:bg-slate-50 active:bg-slate-100 rounded-xl transition-colors text-slate-700 font-medium text-[15px]"
            >
              <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center">
                <ImagePlus className="w-4 h-4 text-emerald-500" />
              </div>
              <span>Thư viện ảnh</span>
            </button>
          </div>
        )}

        <div className="mx-auto bg-white/95 backdrop-blur-xl border-2 border-emerald-100 p-2 rounded-[32px] shadow-[0_15px_40px_-10px_rgba(16,185,129,0.3)] pointer-events-auto transition-all flex items-center gap-1.5 relative z-50">
          <input
            type="file"
            accept="image/*"
            className="hidden"
            ref={galleryInputRef}
            onChange={handleImageUpload}
          />
          <input
            type="file"
            accept="image/jpeg, image/png, image/jpg"
            capture="environment"
            className="hidden"
            ref={cameraInputRef}
            onChange={handleImageUpload}
          />

          {!isRecording && (
            <button
              onClick={() => setShowImageMenu(!showImageMenu)}
              className={`p-2.5 transition-colors rounded-full flex-shrink-0 active:scale-95 ${showImageMenu ? "bg-emerald-100 text-emerald-600" : "text-slate-500 hover:text-emerald-600 bg-slate-100/80 hover:bg-emerald-50"
                }`}
            >
              <ImageIcon className="w-[22px] h-[22px]" />
            </button>
          )}

          <div className="flex-1 relative flex items-center">
            {isRecording ? (
              <div className="w-full flex items-center justify-between px-3 h-[48px] bg-red-50 border border-red-100/80 rounded-full">
                <div className="flex items-center gap-2.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></div>
                  <span className="text-red-500 font-mono font-bold text-[15px] tracking-wide">{formatTime(recordingTime)}</span>
                </div>
                <span className="text-slate-400 text-[13px] font-medium mr-1 animate-pulse select-none">&lt; Trượt để hủy</span>
              </div>
            ) : (
              <>
                <input
                  type="text"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key !== "Enter") return;
                    e.preventDefault();
                    handleSendText();
                  }}
                  placeholder="Hỏi chuyên gia AI..."
                  className="w-full h-[48px] bg-slate-100/80 border-none text-[16px] text-slate-900 rounded-full pl-4 pr-4 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-emerald-500 transition-all placeholder:text-slate-500 font-medium"
                />
              </>
            )}
          </div>

          {trimmedText ? (
            <button
              type="button"
              onClick={() => handleSendText()}
              disabled={isTyping}
              aria-label="Gửi tin nhắn"
              className="p-2.5 bg-emerald-500 text-white rounded-full hover:bg-emerald-600 transition-all shadow-sm active:scale-95 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 flex-shrink-0"
            >
              <Send className="w-[22px] h-[22px] ml-0.5" strokeWidth={2.5} />
            </button>
          ) : (
            <div className="relative">
              {showVoiceTooltip && !isRecording && (
                <div className="absolute -top-[52px] right-0 bg-slate-800 text-white text-[13px] font-semibold px-4 py-2.5 rounded-2xl whitespace-nowrap animate-bounce shadow-lg after:content-[''] after:absolute after:bottom-[-5px] after:right-[14px] after:w-3 after:h-3 after:bg-slate-800 after:rotate-45">
                  Nhấn giữ để nói
                </div>
              )}

              <button
                onPointerDown={handleStartRecording}
                onPointerMove={handlePointerMove}
                onPointerUp={handleStopRecording}
                onPointerCancel={handleCancelRecording}
                onContextMenu={(e) => e.preventDefault()}
                className={`p-2.5 transition-all duration-200 flex-shrink-0 touch-none select-none ${isRecording
                  ? "bg-emerald-500 text-white rounded-full scale-125 shadow-[0_5px_15px_rgba(16,185,129,0.4)] mr-1"
                  : "text-emerald-600 bg-emerald-100/80 hover:bg-emerald-200 rounded-full shadow-sm"
                  }`}
              >
                <Mic className="w-[22px] h-[22px]" />
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
