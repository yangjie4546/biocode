#!/usr/bin/env python3

"""
This is a script to convert GenBank flat files to GFF3 format with a specific focus on
maintaining as much annotation information as possible.

This is not guaranteed to convert all features, but warnings will be printed wherever possible
for features which aren't included.

This is written to handle multi-entry GBK files

Caveats:
- Because the GBK flatfile format doesn't explicitly model parent/child features, this script
  links them using the expected format convention of shared /locus_tag entries for each feature
  of the gene graph (gene, mRNA, CDS)

Author: Joshua Orvis (jorvis AT gmail)
"""

import argparse
from collections import defaultdict
import os
from Bio import SeqIO
import biothings
import biocodegff

def main():
    parser = argparse.ArgumentParser( description='Put a description of your script here')

    ## output file to be written
    parser.add_argument('-i', '--input_file', type=str, required=True, help='Path to an input GBK file' )
    parser.add_argument('-o', '--output_file', type=str, required=True, help='Path to an output GFF file to be created' )
    args = parser.parse_args()

    ofh = open(args.output_file, 'wt')
    ofh.write("##gff-version 3\n")

    assemblies = dict()
    current_assembly = None
    current_gene = None
    current_RNA = None

    rna_count_by_gene = defaultdict(int)
    exon_count_by_RNA = defaultdict(int)

    # each gb_record is a SeqRecord object
    for gb_record in SeqIO.parse(open(args.input_file, "r"), "genbank"):
        mol_id = gb_record.name

        if mol_id not in assemblies:
            assemblies[mol_id] = biothings.Assembly( id=mol_id )

        current_assembly = assemblies[mol_id]
            
        # each feat is a SeqFeature object
        for feat in gb_record.features:
            #print(feat)
            fmin = int(feat.location.start)
            fmax = int(feat.location.end)

            if feat.location.strand == 1:
                strand = '+'
            elif feat.location.strand == -1:
                strand = '-'
            else:
                raise Exception("ERROR: unstranded feature encountered: {0}".format(feat))

            #print("{0} located at {1}-{2} strand:{3}".format( locus_tag, fmin, fmax, strand ) )
            
            if feat.type == 'gene':
                # print the previous gene (if there is one)
                if current_gene is not None:
                    gene.print_as(fh=ofh, source='GenBank', format='gff3')
                
                locus_tag = feat.qualifiers['locus_tag'][0]
                gene = biothings.Gene( id=locus_tag )
                gene.locate_on( target=current_assembly, fmin=fmin, fmax=fmax, strand=strand )
                current_gene = gene

            elif feat.type == 'mRNA':
                locus_tag = feat.qualifiers['locus_tag'][0]
                rna_count_by_gene[locus_tag] += 1
                feat_id = "{0}.mRNA.{1}".format( locus_tag, rna_count_by_gene[locus_tag] )
                
                mRNA = biothings.mRNA( id=feat_id, parent=current_gene )
                mRNA.locate_on( target=current_assembly, fmin=fmin, fmax=fmax, strand=strand )
                gene.add_mRNA(mRNA)
                current_RNA = mRNA

                if feat_id in exon_count_by_RNA:
                    raise Exception( "ERROR: two different mRNAs found with same ID: {0}".format(feat_id) )
                else:
                    exon_count_by_RNA[feat_id] = 0
            
            elif feat.type == 'CDS':
                locus_tag = feat.qualifiers['locus_tag'][0]
                exon_count_by_RNA[current_RNA.id] += 1
                cds_id = "{0}.CDS.{1}".format( current_RNA.id, exon_count_by_RNA[current_RNA.id] )
                CDS = biothings.CDS( id=cds_id, parent=current_RNA )
                CDS.locate_on( target=current_assembly, fmin=fmin, fmax=fmax, strand=strand, phase=0 )
                current_RNA.add_CDS(CDS)

                exon_id = "{0}.exon.{1}".format( current_RNA.id, exon_count_by_RNA[current_RNA.id] )
                exon = biothings.Exon( id=exon_id, parent=current_RNA )
                exon.locate_on( target=current_assembly, fmin=fmin, fmax=fmax, strand=strand )
                current_RNA.add_exon(exon)
                
                product = feat.qualifiers['product'][0]

            else:
                print("WARNING: The following feature was skipped:\n{0}".format(feat))

        # don't forget to do the last gene, if there were any
        if current_gene is not None:
            gene.print_as(fh=ofh, source='GenBank', format='gff3')
            

if __name__ == '__main__':
    main()






