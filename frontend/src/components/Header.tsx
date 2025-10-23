import { Bot } from "lucide-react";
import daganHeaderLogo from "@/assets/DaganHeader.svg";

export const Header = () => {
  return (
    <header className="bg-primary text-white shadow-md">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-center">
          <div className="flex items-center gap-3">
            <img
              src={daganHeaderLogo}
              alt="Dagan"
              className="h-10 object-contain"
            />
          </div>
        </div>
      </div>
    </header>
  );
};