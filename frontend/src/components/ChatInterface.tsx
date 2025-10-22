import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Lightbulb } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import { SourcesFavicons, Source } from "./SourcesFavicons";
import { CitationsPanel } from "./CitationsPanel";
import { StreamingMessage } from "./StreamingMessage";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

const SUGGESTED_QUESTIONS = [
  "Comment obtenir une carte d'identité nationale ?",
  "Quelles sont les démarches pour créer une entreprise ?",
  "Comment renouveler mon passeport ?",
  "Où puis-je payer mes impôts en ligne ?"
];

export const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [selectedSources, setSelectedSources] = useState<Source[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Restore previous conversation from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("chatMessages");
      if (stored) {
        const parsed: Message[] = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setMessages(parsed);
        }
      }
    } catch (e) {
      // ignore
    }
  }, []);

  // Persist conversation locally on changes
  useEffect(() => {
    try {
      localStorage.setItem("chatMessages", JSON.stringify(messages));
    } catch (e) {
      // ignore
    }
  }, [messages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const payload = (text ?? input).trim();
    if (!payload || isLoading) return;

    const userMessage: Message = { role: "user", content: payload };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const { data, error } = await supabase.functions.invoke('chat', {
        body: { 
          messages: [...messages, userMessage],
          systemPrompt: "Tu es Dagan, un assistant IA spécialisé dans l'aide aux démarches administratives togolaises. Ta source de référence principale est le site https://service-public.gouv.tg/. Tu dois fournir des informations exhaustives incluant les heures d'ouverture et les contacts des services administratifs concernés quand c'est pertinent. Si tu ne trouves pas une information, sois honnête et dis-le clairement. Reformule les informations administratives complexes en langage simple et compréhensible."
        }
      });

      if (error) throw error;

      const content = typeof data === 'string'
        ? data
        : (data?.response ?? data?.message ?? "");

      if (!content) {
        throw new Error("Réponse vide du serveur. Vérifiez la configuration de la fonction chat.");
      }

      const assistantMessage: Message = {
        role: "assistant",
        content,
        sources: data?.sources || []
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Error sending message:', error);
      toast({
        title: "Erreur",
        description: (
          typeof error?.message === 'string' && error.message.includes('429')
            ? "Limite de requêtes atteinte. Réessayez dans quelques instants."
            : typeof error?.message === 'string' && error.message.includes('402')
            ? "Crédits insuffisants. Veuillez contacter l'administrateur."
            : error?.message || "Une erreur est survenue lors de l'envoi du message."
        ),
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleSuggestionClick = (question: string) => {
    setInput(question);
    // Send immediately for faster onboarding
    sendMessage(question);
  };

  const handleClearConversation = () => {
    setMessages([]);
    try {
      localStorage.removeItem("chatMessages");
    } catch (e) {
      // ignore
    }
  };

  const handleSourceClick = (sources: Source[]) => {
    setSelectedSources(sources);
    setIsPanelOpen(true);
  };

  return (
    <>
    <Card className={`w-full shadow-2xl border-2 my-8 bg-white/95 backdrop-blur-sm transition-all duration-300 ${isPanelOpen ? 'max-w-3xl' : 'max-w-5xl'}`}>
      <CardHeader className="flex flex-row items-center justify-between px-6 py-4 border-b bg-white">
        <CardTitle className="text-lg font-semibold">Dagan — Assistant civique</CardTitle>
        <div className="flex items-center gap-2">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm" disabled={isLoading}>
                Nouvelle conversation
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Nouvelle conversation</AlertDialogTitle>
                <AlertDialogDescription>
                  Êtes-vous sûr de vouloir commencer une nouvelle conversation ? 
                  L'historique actuel sera supprimé et vous n'aurez plus accès à cette conversation.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction onClick={handleClearConversation}>
                  Continuer
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[60vh] p-6" ref={scrollRef}>
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 space-y-6">
                <div className="text-center space-y-3">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-2">
                    <Bot className="h-8 w-8 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold text-foreground">Bienvenue sur Dagan</h2>
                  <p className="text-muted-foreground max-w-md mx-auto">
                    Votre assistant intelligent pour simplifier vos démarches administratives au Togo. 
                    Posez vos questions et obtenez des réponses claires et précises avec les contacts et horaires des services.
                  </p>
                </div>
                
                <div className="w-full max-w-2xl space-y-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground justify-center">
                    <Lightbulb className="h-4 w-4 text-warning" />
                    <span>Questions suggérées :</span>
                  </div>
                  <div className="grid gap-2">
                    {SUGGESTED_QUESTIONS.map((question, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestionClick(question)}
                        className="text-left px-4 py-3 rounded-lg border-2 border-primary/20 bg-white hover:bg-highlight hover:border-accent hover:shadow-2xl hover:shadow-accent/50 hover:scale-[1.05] transition-all duration-300 text-sm text-foreground font-medium group relative overflow-hidden"
                      >
                        <span className="relative z-10">{question}</span>
                        <div className="absolute inset-0 bg-gradient-to-r from-accent/0 via-accent/30 to-accent/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out"></div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-3 ${
                  message.role === "user" ? "justify-end" : "justify-start"
                } animate-fade-in`}
              >
                {message.role === "assistant" && (
                  <div className="h-8 w-8 rounded-full bg-accent/15 flex items-center justify-center flex-shrink-0">
                    <Bot className="h-5 w-5 text-accent" />
                  </div>
                )}
                
                <div
                  className={`rounded-xl px-4 py-3 max-w-[80%] ${
                    message.role === "user"
                      ? "bg-secondary text-white"
                      : "bg-white border shadow-sm"
                  }`}
                >
                  <div className="flex flex-col">
                    {message.role === "assistant" ? (
                      <StreamingMessage content={message.content} />
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </p>
                    )}
                    {message.role === "assistant" && message.sources && message.sources.length > 0 && (
                      <SourcesFavicons sources={message.sources} onSourceClick={handleSourceClick} />
                    )}
                  </div>
                </div>
                
                {message.role === "user" && (
                  <div className="h-8 w-8 rounded-full bg-primary/15 flex items-center justify-center flex-shrink-0">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                )}
              </div>
            ))}
            
                {isLoading && (
                  <div className="flex gap-3 justify-start animate-fade-in">
                    <div className="h-8 w-8 rounded-full bg-accent/15 flex items-center justify-center">
                      <Bot className="h-5 w-5 text-accent" />
                    </div>
                    <div className="rounded-xl px-4 py-3 bg-white border shadow-sm">
                      <div className="flex gap-1">
                        <div className="h-2 w-2 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="h-2 w-2 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="h-2 w-2 rounded-full bg-accent/60 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </ScrollArea>
        
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Posez votre question sur les démarches administratives..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button 
              onClick={() => sendMessage()} 
              disabled={isLoading || !input.trim()}
              size="icon"
              className="flex-shrink-0 bg-secondary hover:bg-secondary/90"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
    
    <CitationsPanel
      sources={selectedSources}
      isOpen={isPanelOpen}
      onClose={() => setIsPanelOpen(false)}
    />
    </>
  );
};
