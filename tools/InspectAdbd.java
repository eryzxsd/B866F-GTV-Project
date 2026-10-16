// Static inspection only; never executes or changes the Android target.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;

public class InspectAdbd extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs();
  if(args.length!=1)throw new IllegalArgumentException("Expected report path");
  DecompInterface decompiler=new DecompInterface();
  try(PrintWriter out=new PrintWriter(Files.newBufferedWriter(Path.of(args[0])))) {
   out.println("Static adbd EVP_PKEY_cmp caller inspection");
   out.println("SHA256: "+currentProgram.getExecutableSHA256());
   out.println("Language: "+currentProgram.getLanguageID());
   if(!decompiler.openProgram(currentProgram))throw new IllegalStateException(decompiler.getLastMessage());
   HashSet<String> seen=new HashSet<>();
   for(Function function: currentProgram.getFunctionManager().getFunctions(true)) {
    Function target=function.isThunk()?function.getThunkedFunction(true):function;
    if(target==null || !target.getName().contains("EVP_PKEY_cmp"))continue;
    out.println("COMPARE FUNCTION: "+function.getName()+" "+function.getEntryPoint());
    for(Reference ref:getReferencesTo(function.getEntryPoint())) {
     Function caller=getFunctionContaining(ref.getFromAddress());
     out.println("XREF: "+ref.getFromAddress()+" "+ref.getReferenceType());
     if(caller==null || caller.isThunk() || !seen.add(caller.getEntryPoint().toString()))continue;
     out.println("CALLER: "+caller.getName()+" "+caller.getEntryPoint());
     DecompileResults result=decompiler.decompileFunction(caller,60,monitor);
     if(result.decompileCompleted()&&result.getDecompiledFunction()!=null)out.println(result.getDecompiledFunction().getC());
     else out.println("Decompilation unavailable: "+result.getErrorMessage());
    }
   }
   out.println("Limitations: static pseudocode; no exploit or device changes performed.");
  } finally {decompiler.dispose();}
 }
}
