import { Bot } from "lucide-react";
import novatekisLogo from "@/assets/novatekis-logo.png";

export const Header = () => {
  return (
    <header className="bg-primary text-white shadow-md">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="h-8 w-8" />
            <div>
              <h1 className="text-xl font-bold">Dagan</h1>
              <p className="text-sm text-white/90">Assistant Citoyen Intelligent</p>
            </div>
          </div>
          <a 
            href="https://novatekis.com" 
            target="_blank" 
            rel="noopener noreferrer"
            className="hover:opacity-80 transition-opacity"
          >
            <img 
              src={novatekisLogo} 
              alt="Novatekis" 
              className="h-10 object-contain"
            />
          </a>
        </div>
      </div>
    </header>
  );
};
