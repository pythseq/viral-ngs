#!/usr/bin/env python
'''This script contains a number of utilities for filtering NGS reads based
on membership or non-membership in a species / genus / taxonomic grouping.
'''

__author__ = "dpark@broadinstitute.org, irwin@broadinstitute.org"
__version__ = "PLACEHOLDER"
__date__ = "PLACEHOLDER"
__commands__ = []

import argparse, logging, os
import util.cmd, util.file, util.vcf, util.misc
import tools.last, tools.prinseq, tools.trimmomatic

log = logging.getLogger(__name__)


def trimmomatic(inFastq1, inFastq2, pairedOutFastq1, pairedOutFastq2, clipFasta):
	trimmomaticPath = tools.trimmomatic.TrimmomaticTool().install_and_get_path()
	tempUnpaired1 = util.file.mkstempfname()
	tempUnpaired2 = util.file.mkstempfname()
	cmdline = (
		'java -Xmx2g -classpath {trimmomaticPath} '.format(trimmomaticPath = trimmomaticPath) +
			'org.usadellab.trimmomatic.TrimmomaticPE ' +
			' '.join([inFastq1, inFastq2, pairedOutFastq1, tempUnpaired1, pairedOutFastq2, tempUnpaired2]) +
			' LEADING:20 TRAILING:20 SLIDINGWINDOW:4:25 MINLEN:30 ' +
			'ILLUMINACLIP:{clipFasta}:2:30:12 && '.format(clipFasta = clipFasta) +
		'rm {tempUnpaired1} {tempUnpaired2}'.format(tempUnpaired1 = tempUnpaired1, tempUnpaired2 = tempUnpaired2)
			   )
	log.debug(cmdline)
	assert not os.system(cmdline)
	
def parser_trim_trimmomatic():
	parser = argparse.ArgumentParser(
		description='''Trim read sequences with Trimmomatic.''')
	parser.add_argument("inFastq1", help = "Input reads 1")
	parser.add_argument("inFastq2", help = "Input reads 2")
	parser.add_argument("pairedOutFastq1", help = "Paired output 1")
	parser.add_argument("pairedOutFastq2", help = "Paired output 2")
	parser.add_argument("clipFasta", help = "Fasta file with adapters, PCR sequences, etc. to clip off")
		# clipFasta = /idi/sabeti-scratch/kandersen/references/contaminants/contaminants.fasta
	util.cmd.common_args(parser, (('loglevel', None), ('version', None)))

	# Future: handle BAM input and output; handle multiple databases.
	# Will need to implement bam->fastq->bam wrappers that maintain the read metadata
	#parser.add_argument("inBam", help="Input BAM file")
	#parser.add_argument("outBam", help="Output BAM file")

	return parser

def main_trim_trimmomatic(args):
	'''Perhaps move this to a separate script of general bam/alignment utility functions?...'''
	inFastq1 = args.inFastq1
	inFastq2 = args.inFastq2
	pairedOutFastq1 = args.pairedOutFastq1
	pairedOutFastq2 = args.pairedOutFastq2
	clipFasta = args.clipFasta
	trimmomatic(inFastq1, inFastq2, pairedOutFastq1, pairedOutFastq2, clipFasta)
	return 0
__commands__.append(('trim_trimmomatic', main_trim_trimmomatic, parser_trim_trimmomatic))


def filter_lastal(inFastq, refDbs, outFastq):
	tempFilePath = util.file.mkstempfname()
	lastalPath = tools.last.Lastal().install_and_get_path()
	mafSortPath = tools.last.MafSort().install_and_get_path()
	mafConvertPath = tools.last.MafConvert().install_and_get_path()
	prinseqPath = tools.prinseq.PrinseqTool().install_and_get_path()
	noBlastLikeHitsPath = os.path.join(util.file.get_scripts_path(), 'noBlastLikeHits.py')
	
	cmdline = (
		'{lastalPath} -Q1 {refDbs} {inFastq} |'.format(lastalPath = lastalPath, refDbs = refDbs, inFastq = inFastq) +
		'{mafSortPath} -n2 |'.format(mafSortPath = mafSortPath) +
		'{mafConvertPath} tab /dev/stdin > {tempFilePath} &&'.format(
			mafConvertPath = mafConvertPath, tempFilePath = tempFilePath) +
		'python {noBlastLikeHitsPath} -b {tempFilePath} -r {inFastq} -m hit |'.format(noBlastLikeHitsPath = noBlastLikeHitsPath,
			tempFilePath = tempFilePath, inFastq = inFastq) +
		'perl {prinseqPath} -ns_max_n 1 -derep 1 -fastq stdin '.format(prinseqPath = prinseqPath) +
			'-out_bad null -line_width 0 -out_good {outFastq} &&'.format(outFastq = outFastq) +
		'rm {tempFilePath}'.format(tempFilePath = tempFilePath))
	log.debug(cmdline)
	assert not os.system(cmdline)

def parser_filter_lastal():
	parser = argparse.ArgumentParser(
		description = '''Restrict input reads to those that align to the given
		reference database using LASTAL.''')
	parser.add_argument("inFastq", help = "Input fastq file")
	parser.add_argument("refDbs", help = "Reference database to retain from input")
	parser.add_argument("outFastq", help = "Output fastq file")
	util.cmd.common_args(parser, (('loglevel', None), ('version', None)))
	
	# Future: handle BAM input and output; handle multiple databases.
	# Will need to implement bam->fastq->bam wrappers that maintain the read metadata
	#parser.add_argument("inBam", help="Input BAM file")
	#parser.add_argument("outBam", help="Output BAM file")
	
	return parser
def main_filter_lastal(args):
	inFastq = args.inFastq
	refDbs = args.refDbs
	outFastq = args.outFastq
	filter_lastal(inFastq, refDbs, outFastq)
	return 0
__commands__.append(('filter_lastal', main_filter_lastal, parser_filter_lastal))


def deplete_bmtagger(inBam, refDbs):
	''' KGA's "recipe" for human read depletion
#-------- CLEANING OF READS FOR SRA SUBMISSION --------#
# MAKE REQUIRED SUB-DIRECTORIES - DON'T DO THIS IF YOU ALREADY CREATED THESE WITH ANOTHER PIPELINE
for directory in
do
bsub -o ~/log.txt -P sabeti_meta "mkdir $directory/_logs $directory/_temp $directory/_bams $directory/_reports $directory/_pileup $directory/_meta $directory/_reads"
done

# BMTAGGER REMOVAL OF HUMAN READS AND CONTAMINANTS
# Rodent sequences can be removed using mm9_mn, nt_rodent.1 and nt_rodent.2
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
for db1 in GRCh37.68_ncRNA-GRCh37.68_transcripts-HS_rRNA_mitRNA
do
for db2 in hg19
do
for db3 in metagenomics_contaminants_v3 # If you want to remove Lassa, use metagenomics_contaminants_v3_w_lassa, ZEBOV use metagenomics_contaminants_v3_w_zebov
do
bsub -R "rusage[mem=8]" -W 4:00 -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.bt "/idi/sabeti-scratch/kandersen/bin/bmtagger/bmtagger.sh -X -b /idi/sabeti-scratch/kandersen/references/bmtagger/$db1.bitmask -x /idi/sabeti-scratch/kandersen/references/bmtagger/$db1.srprism -T $temp -q1 -1 $directory/_reads/$sample.reads1.fastq -2 $directory/_reads/$sample.reads2.fastq -o $temp/$sample.bmtagger.mrna && /idi/sabeti-scratch/kandersen/bin/bmtagger/bmtagger.sh -X -b /idi/sabeti-scratch/kandersen/references/bmtagger/$db2.bitmask -x /idi/sabeti-scratch/kandersen/references/bmtagger/$db2.srprism -T $temp -q1 -1 $temp/$sample.bmtagger.mrna.1.fastq -2 $temp/$sample.bmtagger.mrna.2.fastq -o $temp/$sample.bmtagger.hg19 && /idi/sabeti-scratch/kandersen/bin/bmtagger/bmtagger.sh -X -b /idi/sabeti-scratch/kandersen/references/bmtagger/$db3.bitmask -x /idi/sabeti-scratch/kandersen/references/bmtagger/$db3.srprism -T $temp -q1 -1 $temp/$sample.bmtagger.hg19.1.fastq -2 $temp/$sample.bmtagger.hg19.2.fastq -o $temp/$sample.bmtagger.contaminants"
done
done
done
done
done
done

# REMOVE DUPLICATES
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
bsub -R "rusage[mem=$memory]" -W 4:00 -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.p1 "/seq/viral/analysis/xyang/programs/M-Vicuna/bin/mvicuna -ipfq $temp/$sample.bmtagger.contaminants.1.fastq,$temp/$sample.bmtagger.contaminants.2.fastq -opfq $temp/$sample.cleaned_reads.prinseq.1.fastq,$temp/$sample.cleaned_reads.prinseq.2.fastq -osfq $temp/$sample.cleaned_reads.unpaired.fastq -drm_op $temp/$sample.bmtagger.hg19.temp1.fastq,$temp/$sample.bmtagger.hg19.temp2.fastq -tasks DupRm"
done
done
done

# REMOVE HUMAN READS AND CONTAMINANTS USING NOVOALIGN
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
bsub -W 4:00 -q hour -R "rusage[mem=4]" -n 4 -R "span[hosts=1]" -o $directory/_logs/$sample.log.bsub.txt -P sabeti_align -J $sample.al "/idi/sabeti-scratch/kandersen/bin/novocraft/novoalign -c 4 -f $temp/$sample.cleaned_reads.prinseq.1.fastq $temp/$sample.cleaned_reads.prinseq.2.fastq -r Random -l 30 -g 20 -x 6 -t 502 -F STDFQ -d /idi/sabeti-scratch/kandersen/references/novo_clean/metag_v3.ncRNA.mRNA.mitRNA.consensus.nix -o SAM $'@RG\tID:140813.$sample\tSM:$sample\tPL:Illumina\tPU:HiSeq\tLB:BroadPE\tCN:Broad' 2> $directory/_logs/$sample.log.novoalign.txt | java -Xmx2g -jar /seq/software/picard/current/bin/SortSam.jar SO=coordinate I=/dev/stdin O=$directory/_temp/$sample.sorted.bam CREATE_INDEX=true && samtools view -b -f 4 -u $directory/_temp/$sample.sorted.bam > $directory/_temp/$sample.depleted.bam && java -Xmx2g -jar /seq/software/picard/current/bin/SamToFastq.jar INPUT=$directory/_temp/$sample.depleted.bam FASTQ=$directory/_temp/$sample.novo.depleted.reads1.fastq SECOND_END_FASTQ=$directory/_temp/$sample.novo.depleted.reads2.fastq VALIDATION_STRINGENCY=SILENT && /idi/sabeti-scratch/kandersen/bin/prinseq/prinseq-lite.pl -out_format 1 -line_width 0 -fastq $directory/_temp/$sample.novo.depleted.reads1.fastq -out_good $directory/_temp/$sample.prinseq.1 -out_bad null && /idi/sabeti-scratch/kandersen/bin/prinseq/prinseq-lite.pl -out_format 1 -line_width 0 -fastq $directory/_temp/$sample.novo.depleted.reads2.fastq -out_good $directory/_temp/$sample.prinseq.2 -out_bad null"
done
done
done

# SPLIT FILES FOR BLASTN ANALYSIS
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
bsub -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.sf "split -a 3 -l 20000 $directory/_temp/$sample.prinseq.1.fasta $temp/$sample.prinseq.1.split."
bsub -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.sf "split -a 3 -l 20000 $directory/_temp/$sample.prinseq.2.fasta $temp/$sample.prinseq.2.split."
done
done
done

# RUN BLASTN ANALYSIS
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
for db in metag_v3.ncRNA.mRNA.mitRNA.consensus
do
i=1
j=1
for a in $temp/$sample.prinseq.1.split.*
do
bsub -R "rusage[mem=2]" -W 4:00 -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.$((j++)).bn "blastn -db /idi/sabeti-scratch/kandersen/references/blast/$db -word_size 16 -evalue 1e-6 -outfmt 6 -num_descriptions 2 -num_alignments 2 -query $a -out $temp/$sample.1.$db.$((i++)).txt"
done
done
done
done
done
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
for db in metag_v3.ncRNA.mRNA.mitRNA.consensus
do
i=1
j=1
for b in $temp/$sample.prinseq.2.split.*
do
bsub -R "rusage[mem=$memory]" -W 4:00 -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.$((j++)).bn "blastn -db /idi/sabeti-scratch/kandersen/references/blast/$db -word_size 16 -evalue 1e-6 -outfmt 6 -num_descriptions 2 -num_alignments 2 -query $b -out $temp/$sample.2.$db.$((i++)).txt"
done
done
done
done
done

# CONCATENATE BLASTN RESULTS
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
bsub -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.c1 "cat $temp/$sample.1.*.*.txt > $directory/_temp/$sample.blast.1.txt"
bsub -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.c2 "cat $temp/$sample.2.*.*.txt > $directory/_temp/$sample.blast.2.txt"
done
done
done

# EXTRACT READS WITH NO BLAST HITS
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
bsub -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.nb "python /idi/sabeti-scratch/kandersen/bin/scripts/noBlastHits_v3.py -b $directory/_temp/$sample.blast.1.txt -r $directory/_temp/$sample.novo.depleted.reads1.fastq -m nohit > $temp/$sample.nohits.1.fastq"
bsub -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.nb "python /idi/sabeti-scratch/kandersen/bin/scripts/noBlastHits_v3.py -b $directory/_temp/$sample.blast.2.txt -r $directory/_temp/$sample.novo.depleted.reads2.fastq -m nohit > $temp/$sample.nohits.2.fastq"
done
done
done

# FIX MATE-PAIR INFORMATION
for sample in
do
for directory in
do
for temp in /broad/hptmp/andersen
do
bsub -R "rusage[mem=4]" -W 4:00 -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.fm "/idi/sabeti-scratch/kandersen/bin/scripts/mergeShuffledFastqSeqs.pl -t -r '^@(\S+)/[1|2]$' -f1 $temp/$sample.nohits.1.fastq -f2 $temp/$sample.nohits.2.fastq -o $directory/_temp/$sample.cleaned"
done
done
done

# GET NON-VIRAL AND VIRAL READS
for sample in
do
for directory in
do
for reference in $directory/_refs/zaire_guinea.nix
do
bsub -q week -W 24:00 -R "rusage[mem=2]" -n 1 -R "span[hosts=1]" -o $directory/_logs/$sample.log.bsub.txt -P sabeti_align -J $sample.a2 "/idi/sabeti-scratch/kandersen/bin/novocraft_v3/novoalign -c 1 -f $directory/_reads/$sample.reads1.fastq $directory/_reads/$sample.reads2.fastq -r Random -l 40 -g 20 -x 6 -t 502 -F STDFQ -d $reference -o SAM $'@RG\tID:$sample\tSM:$sample\tPL:Illumina\tPU:HiSeq\tLB:BroadPE\tCN:Broad' 2> $directory/_logs/$sample.log.viral.txt | java -Xmx2g -jar /seq/software/picard/current/bin/SortSam.jar SO=coordinate I=/dev/stdin O=$directory/_temp/$sample.sorted3.bam CREATE_INDEX=true && samtools view -b -q 1 -u $directory/_temp/$sample.sorted3.bam | java -Xmx2g -jar /seq/software/picard/current/bin/SortSam.jar SO=coordinate I=/dev/stdin O=$directory/_temp/$sample.mapped3.bam CREATE_INDEX=true VALIDATION_STRINGENCY=SILENT && java -Xmx2g -jar /seq/software/picard/current/bin/MarkDuplicates.jar I=$directory/_temp/$sample.mapped3.bam O=$directory/_temp/$sample.mappedNoDub3.bam METRICS_FILE=$directory/_temp/$sample.log.markdups3.txt CREATE_INDEX=true REMOVE_DUPLICATES=true && java -Xmx2g -jar /seq/software/picard/current/bin/SamToFastq.jar INPUT=$directory/_temp/$sample.mappedNoDub3.bam FASTQ=$directory/_temp/$sample.viral.reads1.fastq SECOND_END_FASTQ=$directory/_temp/$sample.viral.reads2.fastq VALIDATION_STRINGENCY=SILENT"
bsub -q hour -W 4:00 -R "rusage[mem=2]" -n 1 -R "span[hosts=1]" -o $directory/_logs/$sample.log.bsub.txt -P sabeti_align -J $sample.a1 "/idi/sabeti-scratch/kandersen/bin/novocraft_v3/novoalign -c 1 -f $directory/_temp/$sample.cleaned.1.fastq $directory/_temp/$sample.cleaned.2.fastq -r Random -l 40 -g 20 -x 6 -t 502 -F STDFQ -d $reference -o SAM $'@RG\tID:$sample\tSM:$sample\tPL:Illumina\tPU:HiSeq\tLB:BroadPE\tCN:Broad' 2> $directory/_logs/$sample.log.viral-deplete.txt | java -Xmx2g -jar /seq/software/picard/current/bin/SortSam.jar SO=coordinate I=/dev/stdin O=$directory/_temp/$sample.sorted2.bam CREATE_INDEX=true && samtools view -b -f 4 -u $directory/_temp/$sample.sorted2.bam > $directory/_temp/$sample.depleted2.bam && java -Xmx2g -jar /seq/software/picard/current/bin/SamToFastq.jar INPUT=$directory/_temp/$sample.depleted2.bam FASTQ=$directory/_temp/$sample.viral.depleted.reads1.fastq SECOND_END_FASTQ=$directory/_temp/$sample.viral.depleted.reads2.fastq VALIDATION_STRINGENCY=SILENT"
done
done
done

# COMBINE READS
for sample in
do
for directory in
do
bsub -R "rusage[mem=4]" -W 4:00 -o $directory/_logs/$sample.log.bsub.txt -P sabeti_meta -J $sample.fm "cat $directory/_temp/$sample.viral.depleted.reads1.fastq $directory/_temp/$sample.viral.reads1.fastq > $directory/_reads/$sample.cleaned.1.fastq && cat $directory/_temp/$sample.viral.depleted.reads2.fastq $directory/_temp/$sample.viral.reads2.fastq > $directory/_reads/$sample.cleaned.2.fastq"
done
done

# CONVERT TO BAM FILE
for sample in
do
for directory in
do
for date in
do
bsub -W 4:00 -q hour -R "rusage[mem=2]" -n 1 -R "span[hosts=1]" -o $directory/_logs/$sample.log.bsub.txt -P sabeti_align -J $sample.BF "java -Xmx2g -jar /seq/software/picard/current/bin/FastqToSam.jar FASTQ=$directory/_reads/$sample.cleaned.1.fastq FASTQ2=$directory/_reads/$sample.cleaned.2.fastq OUTPUT=$directory/_bams/$sample.bam SAMPLE_NAME=$sample LIBRARY_NAME=$sample PLATFORM=illumina SEQUENCING_CENTER=broad RUN_DATE=$date CREATE_MD5_FILE=True"
done
done
done
	'''
	raise ("not yet implemented")


def parser_deplete_bmtagger():
	parser = argparse.ArgumentParser(
		description='''Deplete human reads and other contaminants using bmtagger''')
	parser.add_argument("inBam", help="Input BAM file")
	parser.add_argument("refDbs", nargs='+',
		help="""Reference databases (one or more) to deplete from input""")
	parser.add_argument("outBam", help="Output BAM file")
	util.cmd.common_args(parser, (('loglevel',None), ('version',None)))
	return parser
def main_deplete_bmtagger(args):
	raise ("not yet implemented")
	return 0
__commands__.append(('deplete_bmtagger', main_deplete_bmtagger, parser_deplete_bmtagger))


if __name__ == '__main__':
	util.cmd.main_argparse(__commands__, __doc__)