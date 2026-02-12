import React from "react";
import Image from "next/image";

interface LogoProps {
    isCollapsed: boolean;
}

const Logo = React.forwardRef<HTMLDivElement, LogoProps>(({ isCollapsed }, ref) => {
  if (isCollapsed) {
    return (
      <div ref={ref} className="flex items-center justify-start mb-2 p-0">
        <Image src="/logo-collapsed.png" alt="Logo" width={40} height={32} />
      </div>
    );
  }

  return (
    <div ref={ref} className="text-lg text-center border rounded-full bg-blue-50 border-white font-semibold text-gray-700 mb-2 block items-center">
      <span>Syncnergy 智能会议助手</span>
    </div>
  );
});

Logo.displayName = "Logo";

export default Logo;