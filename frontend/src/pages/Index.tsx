import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ChatInterface } from "@/components/ChatInterface";
import togoRibbon from "@/assets/togo-ribbon.png";

const Index = () => {
  return (
    <div className="min-h-screen flex flex-col bg-muted/30 relative">
      <div className="absolute inset-0 bg-togo-pattern pointer-events-none" />
      <Header />
      <div className="w-full h-3 overflow-hidden">
        <img 
          src={togoRibbon} 
          alt="" 
          className="w-full h-full object-cover object-center"
        />
      </div>
      <main className="flex-1 flex items-center justify-center p-4 relative z-10">
        <ChatInterface />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
