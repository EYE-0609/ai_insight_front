import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '产业知识图谱工作台',
  description: '独立运行的产业链知识图谱前端与联调工作台',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
