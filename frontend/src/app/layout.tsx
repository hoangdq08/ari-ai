import type { Metadata } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import "./globals.css";
import { TopHeader } from "@/shared/components/layout/TopHeader";
import { BottomNav } from "@/shared/components/layout/BottomNav";
import QueryProvider from "@/core/providers/QueryProvider";

const beVietnamPro = Be_Vietnam_Pro({ 
  subsets: ["vietnamese", "latin"],
  weight: ["400", "500", "600", "700", "800"]
});

export const metadata: Metadata = {
  title: "Nông Trí AI - Trợ lý Nông nghiệp",
  description: "Trợ lý ảo tư vấn nông nghiệp thông minh",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className={`${beVietnamPro.className} bg-slate-100 text-slate-900 overflow-x-hidden min-h-screen flex justify-center`}>
        <QueryProvider>
          {/* Mobile Simulator Frame */}
          <div className="w-full max-w-[448px] bg-white min-h-screen relative shadow-[0_0_40px_rgba(0,0,0,0.08)] flex flex-col">
            {/* Decorative background blob */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-b from-emerald-50 to-transparent blur-[100px] pointer-events-none z-0"></div>
            
            <TopHeader />
            
            <main className="flex-1 relative z-10 pb-20">
              {children}
            </main>
            
            <BottomNav />
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
