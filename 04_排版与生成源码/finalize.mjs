import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const SOURCE=path.dirname(fileURLToPath(import.meta.url));
const W=path.dirname(SOURCE), B=path.join(SOURCE,'.build');
await fs.mkdir(B,{recursive:true});
const settings=JSON.parse(await fs.readFile(path.join(SOURCE,'runtime-settings.json'),'utf8'));
const SKILL=process.env.PRESENTATIONS_SKILL_DIR||settings.presentationsSkillDir;
process.env.RUNTIME_NODE_MODULES=process.env.RUNTIME_NODE_MODULES||settings.nodeModules;
const stamp=new Date().toISOString().replace(/[-:]/g,'').slice(0,15);
const finalPath=path.join(W,'01_汇报材料/修订输出',`课程汇报_修订_${stamp}.pptx`);
await fs.mkdir(path.dirname(finalPath),{recursive:true});
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
try {
const r=await finalizePresentation({workspaceDir:W,candidatePath:path.join(B,'candidate-v2.pptx'),finalPath,
pythonExecutable:process.env.PRESENTATIONS_PYTHON||settings.pythonExecutable,
integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','12'],
explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[12],requiredNativeChartOwnerSlides:[8],materializeLiteralChartWorkbooks:true,
fontPolicy:{basis:'design',families:['Microsoft YaHei']},verifyArtifactToolImport:true,receiptPath:path.join(B,'v2.validation.json')});
console.log('finalized',r.finalPath);
} catch(e) {
await fs.writeFile(path.join(B,'finalizer-error.json'),JSON.stringify({message:e.message,stack:e.stack,...e},null,2));
console.error(e);process.exitCode=1;
}
