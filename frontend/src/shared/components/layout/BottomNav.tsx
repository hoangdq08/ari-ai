"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, MessageSquare, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

export function BottomNav() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Trang chủ', href: '/', icon: Home },
    { name: 'Hỏi AI', href: '/chat', icon: MessageSquare },
    { name: 'Cẩm nang', href: '/handbook', icon: BookOpen },
  ];

  if (pathname === '/chat') return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-[448px] px-4 z-50 safe-area-pb pointer-events-none">
      <nav className="mx-auto h-[68px] bg-white/85 backdrop-blur-xl border border-white/60 shadow-[0_8px_32px_rgba(0,0,0,0.08)] rounded-[32px] pointer-events-auto relative overflow-hidden">
        <div className="flex h-full items-center justify-around px-2 relative z-10">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className="relative flex flex-col items-center justify-center w-20 h-full transition-colors group"
              >
                {isActive && (
                  <motion.div 
                    layoutId="activeTab"
                    className="absolute inset-0 bg-emerald-100/60 scale-[0.9] rounded-[24px]"
                    transition={{ type: "spring", stiffness: 400, damping: 25 }}
                  />
                )}
                <div className="relative z-10 flex flex-col items-center mt-1 transition-transform duration-300 group-hover:-translate-y-0.5">
                  <Icon 
                    className={cn(
                      "w-[24px] h-[24px] mb-1 transition-all duration-300", 
                      isActive 
                        ? "text-emerald-700 stroke-[2.5px] scale-125 -translate-y-0.5" 
                        : "text-slate-500 group-hover:text-emerald-600 group-hover:scale-110 stroke-[2px]"
                    )} 
                  />
                  <span className={cn(
                    "text-[10px] transition-all duration-300", 
                    isActive 
                      ? "font-extrabold text-emerald-800" 
                      : "font-bold text-slate-500 group-hover:text-emerald-600"
                  )}>
                    {item.name}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
