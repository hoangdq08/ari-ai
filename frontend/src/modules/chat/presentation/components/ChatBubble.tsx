import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { User, Bot, BookOpen, X } from "lucide-react";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { cn } from "@/lib/utils";

interface ChatBubbleProps {
  role: "user" | "ai";
  content: string;
  citation?: string;
  imageUrl?: string;
}

export function ChatBubble({
  role,
  content,
  citation,
  imageUrl,
}: ChatBubbleProps) {
  const isUser = role === "user";
  const [isZoomed, setIsZoomed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div
      className={cn(
        "flex w-full mt-4 space-x-3 px-4",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center border border-emerald-200">
          <Bot className="w-5 h-5 text-emerald-600" />
        </div>
      )}

      <div
        className={cn(
          "flex flex-col gap-1 max-w-[82%]",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "rounded-[20px] text-[16px] leading-relaxed font-medium overflow-hidden",
            content || !imageUrl ? "p-4" : "p-1.5",
            isUser && (content || !imageUrl)
              ? "bg-gradient-to-br from-emerald-500 to-teal-500 text-white rounded-br-sm shadow-[0_4px_15px_rgba(16,185,129,0.2)]"
              : "",
            !isUser && (content || !imageUrl)
              ? "bg-white border-2 border-slate-200 text-slate-900 rounded-bl-sm shadow-sm"
              : "",
            isUser && !content && imageUrl
              ? "bg-slate-100 rounded-br-sm shadow-sm border border-slate-200"
              : "",
          )}
        >
          {imageUrl && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={imageUrl}
              alt="Uploaded"
              onClick={() => setIsZoomed(true)}
              className={cn(
                "w-full max-w-[220px] rounded-[14px] object-cover cursor-pointer hover:opacity-90 transition-opacity",
                content ? "mb-2 border border-black/10" : "mb-0",
              )}
            />
          )}
          {content && <span>{content}</span>}
        </div>

        {/* Hộp trích dẫn hiển thị minh bạch nguồn gốc (Reliability) */}
        {!isUser && citation && (
          <div className="mt-1.5 flex items-start gap-2 bg-amber-50/80 border-2 border-amber-200 rounded-xl p-3 text-[13px] text-amber-900 shadow-sm max-w-full min-w-0">
            <BookOpen
              className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600"
              strokeWidth={2.5}
            />
            <span className="font-semibold leading-snug min-w-0 break-words">
              Trích xuất:{" "}
              <span className="font-bold text-amber-950">{citation}</span>
            </span>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center border border-slate-300">
          <User className="w-5 h-5 text-slate-600" />
        </div>
      )}

      {/* Fullscreen Image Modal via Portal */}
      {mounted &&
        isZoomed &&
        imageUrl &&
        createPortal(
          <div
            className="fixed inset-0 z-[99999] bg-black/95 flex items-center justify-center animate-in fade-in duration-200"
            onClick={() => setIsZoomed(false)}
          >
            <button
              className="absolute top-4 right-4 z-[100000] p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors shadow-sm"
              onClick={(e) => {
                e.stopPropagation();
                setIsZoomed(false);
              }}
            >
              <X className="w-6 h-6" />
            </button>

            <div
              className="w-full h-full flex items-center justify-center cursor-move"
              onClick={(e) => e.stopPropagation()}
            >
              <TransformWrapper
                initialScale={1}
                minScale={0.5}
                maxScale={5}
                centerOnInit={true}
                wheel={{ step: 0.1 }}
              >
                <TransformComponent
                  wrapperStyle={{ width: "100%", height: "100%" }}
                  contentStyle={{
                    width: "100%",
                    height: "100%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl}
                    alt="Zoomed Upload"
                    className="max-w-full max-h-[100dvh] object-contain select-none"
                    draggable={false}
                  />
                </TransformComponent>
              </TransformWrapper>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
