"use client";

import { Mic, Camera } from 'lucide-react';
import Link from 'next/link';
import { motion } from 'framer-motion';

export function BigActionMenu() {
  return (
    <div className="flex flex-col gap-6 w-full max-w-sm mx-auto px-4 mt-8 relative z-10">
      {/* Nút Ghi âm siêu to - Vibrant Emerald Gradient */}
      <motion.div whileTap={{ scale: 0.96 }} whileHover={{ y: -4 }}>
        <Link href="/chat?mode=voice" className="group relative w-full aspect-[4/3] flex flex-col items-center justify-center rounded-[32px] border border-emerald-300/50 shadow-[0_15px_35px_rgba(16,185,129,0.2)] overflow-hidden bg-emerald-500">
          {/* Animated Gradient Background */}
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 via-emerald-500 to-teal-500 opacity-90 group-hover:opacity-100 transition-opacity duration-500"></div>
          
          <div className="relative z-10 w-24 h-24 bg-white/20 backdrop-blur-md border border-white/40 rounded-full flex items-center justify-center mb-5 shadow-[0_8px_25px_rgba(4,120,87,0.2)] group-hover:shadow-[0_12px_30px_rgba(4,120,87,0.3)] transition-all duration-300">
            <Mic className="w-12 h-12 text-white drop-shadow-sm" strokeWidth={2.5} />
          </div>
          <h2 className="relative z-10 text-[26px] font-extrabold text-white tracking-tight drop-shadow-sm">Hỏi bằng giọng nói</h2>
          <p className="relative z-10 text-emerald-50 mt-1.5 text-center px-4 font-medium text-[15px]">Nhấn vào đây để đặt câu hỏi trực tiếp</p>
        </Link>
      </motion.div>

      {/* Nút Chụp ảnh siêu to - Vibrant Blue Gradient */}
      <motion.div whileTap={{ scale: 0.96 }} whileHover={{ y: -4 }}>
        <Link href="/chat?mode=camera" className="group relative w-full aspect-[4/3] flex flex-col items-center justify-center rounded-[32px] border border-blue-300/50 shadow-[0_15px_35px_rgba(59,130,246,0.2)] overflow-hidden bg-blue-500">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-400 via-blue-500 to-indigo-500 opacity-90 group-hover:opacity-100 transition-opacity duration-500"></div>
          
          <div className="relative z-10 w-24 h-24 bg-white/20 backdrop-blur-md border border-white/40 rounded-full flex items-center justify-center mb-5 shadow-[0_8px_25px_rgba(30,58,138,0.2)] group-hover:shadow-[0_12px_30px_rgba(30,58,138,0.3)] transition-all duration-300">
            <Camera className="w-12 h-12 text-white drop-shadow-sm" strokeWidth={2.5} />
          </div>
          <h2 className="relative z-10 text-[26px] font-extrabold text-white tracking-tight drop-shadow-sm">Chụp ảnh sâu bệnh</h2>
          <p className="relative z-10 text-blue-50 mt-1.5 text-center px-4 font-medium text-[15px]">Gửi ảnh cây trồng để nhận chẩn đoán ngay</p>
        </Link>
      </motion.div>
    </div>
  );
}
